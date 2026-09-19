"""
Tree-sitter TypeScript and JavaScript Symbol Parser.

Purpose:
Statically inspects JavaScript (.js, .jsx) and TypeScript (.ts, .tsx) source files
using Tree-sitter concrete syntax tree (CST) parsing.
Extracts functions, async functions, classes, methods, and imports without executing code.

Architectural Note:
- Python files continue to use Python's native `ast` module (PythonParser) for speed and simplicity.
- Tree-sitter is used for multi-language AST symbol extraction (JS/TS/Java/Go).
- All parsers produce the unified SymbolItem schema.
"""

import logging
import os
from typing import List, Optional

from tree_sitter import Language, Node, Parser
import tree_sitter_javascript
import tree_sitter_typescript

from app.schemas.symbols import SymbolItem, SymbolKind
from app.services.parser.base import BaseLanguageParser

logger = logging.getLogger(__name__)


class TypeScriptTreeSitterParser(BaseLanguageParser):
    """Static Tree-sitter symbol parser for TypeScript and JavaScript files."""

    def __init__(self):
        # Initialize languages
        self._ts_lang = Language(tree_sitter_typescript.language_typescript())
        self._tsx_lang = Language(tree_sitter_typescript.language_tsx())
        self._js_lang = Language(tree_sitter_javascript.language())

    def _get_parser_for_extension(self, ext: str) -> Parser:
        """Selects appropriate Tree-sitter Parser based on file extension."""
        ext = ext.lower()
        if ext in (".tsx", ".jsx"):
            return Parser(self._tsx_lang)
        elif ext == ".js":
            return Parser(self._js_lang)
        else:
            return Parser(self._ts_lang)

    def _clean_docstring(self, raw_comment: str) -> Optional[str]:
        """Cleans JS/TS comment blocks into readable docstrings."""
        if not raw_comment:
            return None
        lines = raw_comment.strip().splitlines()
        cleaned_lines = []
        for line in lines:
            l = line.strip()
            if l.startswith("/**"):
                l = l[3:].strip()
            if l.endswith("*/"):
                l = l[:-2].strip()
            elif l.startswith("*"):
                l = l[1:].strip()
            elif l.startswith("//"):
                l = l[2:].strip()
            if l:
                cleaned_lines.append(l)
        return "\n".join(cleaned_lines) if cleaned_lines else None

    def _get_docstring(self, node: Node, source_text: str) -> Optional[str]:
        """Extracts preceding comment docstring if present."""
        prev = node.prev_sibling
        if prev and prev.type == "comment":
            raw_comment = source_text[prev.start_byte:prev.end_byte]
            return self._clean_docstring(raw_comment)
        return None

    def _get_node_text(self, node: Node, source_text: str) -> str:
        """Extracts exact substring for an AST node."""
        return source_text[node.start_byte:node.end_byte]

    def _get_signature(self, node: Node, source_text: str) -> str:
        """Extracts concise single-line signature from node definition."""
        text = self._get_node_text(node, source_text)
        first_line = text.splitlines()[0].strip()
        if first_line.endswith(";"):
            first_line = first_line[:-1].strip()
        if first_line.endswith("{"):
            first_line = first_line[:-1].strip()
        return first_line

    def parse_file(self, file_path: str, relative_path: str) -> List[SymbolItem]:
        """
        Statically parses a JS/JSX/TS/TSX file into Tree-sitter CST nodes and extracts symbols.
        Returns an empty list gracefully on reading or unhandled errors.
        """
        try:
            with open(file_path, "rb") as f:
                source_bytes = f.read()

            source_text = source_bytes.decode("utf-8", errors="replace")
            _, ext = os.path.splitext(relative_path.lower())
            parser = self._get_parser_for_extension(ext)

            tree = parser.parse(source_bytes)
            symbols: List[SymbolItem] = []

            self._traverse_node(tree.root_node, source_text, relative_path, symbols)
            return symbols
        except Exception as exc:
            logger.warning(f"Failed to parse symbols in '{relative_path}': {str(exc)}")
            return []

    def _traverse_node(
        self,
        node: Node,
        source_text: str,
        relative_path: str,
        symbols: List[SymbolItem],
        class_stack: Optional[List[str]] = None,
    ):
        """Recursively traverses Tree-sitter CST nodes to extract symbol definitions."""
        if class_stack is None:
            class_stack = []

        node_type = node.type

        # Unwrap export_statement (e.g. `export class Foo`, `export default function bar()`)
        if node_type in ("export_statement", "export_default_declaration"):
            for child in node.children:
                if child.type in (
                    "class_declaration",
                    "function_declaration",
                    "lexical_declaration",
                    "variable_declaration",
                    "interface_declaration",
                ):
                    self._traverse_node(child, source_text, relative_path, symbols, class_stack)
            return

        # 1. Imports
        if node_type == "import_statement":
            signature = self._get_signature(node, source_text)
            symbols.append(
                SymbolItem(
                    name=signature,
                    kind=SymbolKind.IMPORT,
                    file_path=relative_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=signature,
                    docstring=None,
                )
            )
            return

        # 2. Classes
        elif node_type == "class_declaration":
            name_node = node.child_by_field_name("name")
            class_name = (
                self._get_node_text(name_node, source_text)
                if name_node
                else "AnonymousClass"
            )
            signature = self._get_signature(node, source_text)
            docstring = self._get_docstring(node, source_text)

            symbols.append(
                SymbolItem(
                    name=class_name,
                    kind=SymbolKind.CLASS,
                    file_path=relative_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=signature,
                    docstring=docstring,
                )
            )

            # Traverse class body for methods
            body_node = node.child_by_field_name("body")
            if body_node:
                new_class_stack = class_stack + [class_name]
                for child in body_node.children:
                    self._traverse_node(
                        child, source_text, relative_path, symbols, new_class_stack
                    )
            return

        # 3. Methods inside Class Body
        elif node_type in ("method_definition", "abstract_method_signature", "method_signature"):
            if class_stack:
                name_node = node.child_by_field_name("name")
                method_name = (
                    self._get_node_text(name_node, source_text)
                    if name_node
                    else "method"
                )
                signature = self._get_signature(node, source_text)
                docstring = self._get_docstring(node, source_text)

                symbols.append(
                    SymbolItem(
                        name=method_name,
                        kind=SymbolKind.METHOD,
                        file_path=relative_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        signature=signature,
                        docstring=docstring,
                    )
                )
            return

        # 4. Functions (Standalone & Async)
        elif node_type in ("function_declaration", "generator_function_declaration"):
            name_node = node.child_by_field_name("name")
            func_name = (
                self._get_node_text(name_node, source_text)
                if name_node
                else "anonymous"
            )
            kind = SymbolKind.METHOD if class_stack else SymbolKind.FUNCTION
            signature = self._get_signature(node, source_text)
            docstring = self._get_docstring(node, source_text)

            symbols.append(
                SymbolItem(
                    name=func_name,
                    kind=kind,
                    file_path=relative_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=signature,
                    docstring=docstring,
                )
            )
            return

        # 5. Variable Arrow Functions / Function Expressions (`const foo = () => {}`)
        elif node_type in ("lexical_declaration", "variable_declaration"):
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")

                    if name_node and value_node and value_node.type in (
                        "arrow_function",
                        "function_expression",
                    ):
                        func_name = self._get_node_text(name_node, source_text)
                        kind = SymbolKind.METHOD if class_stack else SymbolKind.FUNCTION
                        signature = self._get_signature(node, source_text)
                        docstring = self._get_docstring(node, source_text)

                        symbols.append(
                            SymbolItem(
                                name=func_name,
                                kind=kind,
                                file_path=relative_path,
                                line_start=node.start_point[0] + 1,
                                line_end=node.end_point[0] + 1,
                                signature=signature,
                                docstring=docstring,
                            )
                        )
            return

        # Traverse general children
        for child in node.children:
            self._traverse_node(child, source_text, relative_path, symbols, class_stack)

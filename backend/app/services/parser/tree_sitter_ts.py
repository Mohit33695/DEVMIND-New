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

    def _extract_parameters(self, node: Node, source_text: str) -> Optional[List[str]]:
        """Extracts formal parameter names from a function or method node."""
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            # Fallback to checking children for formal_parameters
            for child in node.children:
                if child.type == "formal_parameters":
                    params_node = child
                    break
        if not params_node:
            return None

        param_names = []
        for child in params_node.children:
            if child.type in ("required_parameter", "optional_parameter", "rest_parameter"):
                pattern = child.child_by_field_name("pattern") or child.child_by_field_name("name")
                if pattern:
                    param_names.append(self._get_node_text(pattern, source_text).strip())
                else:
                    text = self._get_node_text(child, source_text).split(":")[0].strip()
                    if text and text not in ("(", ")", ","):
                        param_names.append(text)
            elif child.type == "identifier":
                param_names.append(self._get_node_text(child, source_text).strip())
        return param_names if param_names else None

    def _extract_return_type(self, node: Node, source_text: str) -> Optional[str]:
        """Extracts return type annotation string if present."""
        ret_node = node.child_by_field_name("return_type")
        if not ret_node:
            for child in node.children:
                if child.type == "type_annotation":
                    ret_node = child
                    break
        if ret_node:
            text = self._get_node_text(ret_node, source_text).strip()
            if text.startswith(":"):
                text = text[1:].strip()
            return text if text else None
        return None

    def _extract_visibility(self, node: Node, source_text: str, is_exported: bool = False) -> Optional[str]:
        """Extracts accessibility modifier (public/private/protected) or export status."""
        for child in node.children:
            if child.type in ("accessibility_modifier", "accessibility"):
                return self._get_node_text(child, source_text).strip()
        if is_exported:
            return "export"
        return None

    def _traverse_node(
        self,
        node: Node,
        source_text: str,
        relative_path: str,
        symbols: List[SymbolItem],
        class_stack: Optional[List[str]] = None,
        is_exported: bool = False,
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
                    self._traverse_node(child, source_text, relative_path, symbols, class_stack, is_exported=True)
            return

        parent_class = class_stack[-1] if class_stack else None

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
                    parent_symbol=None,
                    parameters=None,
                    return_type=None,
                    visibility=None,
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
            visibility = self._extract_visibility(node, source_text, is_exported)

            symbols.append(
                SymbolItem(
                    name=class_name,
                    kind=SymbolKind.CLASS,
                    file_path=relative_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=signature,
                    docstring=docstring,
                    parent_symbol=None,
                    parameters=None,
                    return_type=None,
                    visibility=visibility,
                )
            )

            # Traverse class body for methods
            body_node = node.child_by_field_name("body")
            if body_node:
                new_class_stack = class_stack + [class_name]
                for child in body_node.children:
                    self._traverse_node(
                        child, source_text, relative_path, symbols, new_class_stack, is_exported=False
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
                params = self._extract_parameters(node, source_text)
                ret_type = self._extract_return_type(node, source_text)
                visibility = self._extract_visibility(node, source_text, is_exported)

                symbols.append(
                    SymbolItem(
                        name=method_name,
                        kind=SymbolKind.METHOD,
                        file_path=relative_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        signature=signature,
                        docstring=docstring,
                        parent_symbol=parent_class,
                        parameters=params,
                        return_type=ret_type,
                        visibility=visibility,
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
            params = self._extract_parameters(node, source_text)
            ret_type = self._extract_return_type(node, source_text)
            visibility = self._extract_visibility(node, source_text, is_exported)

            symbols.append(
                SymbolItem(
                    name=func_name,
                    kind=kind,
                    file_path=relative_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=signature,
                    docstring=docstring,
                    parent_symbol=parent_class,
                    parameters=params,
                    return_type=ret_type,
                    visibility=visibility,
                )
            )
            return

        # 5. Variable Arrow Functions / Function Expressions (`const foo = () => {}`)
        elif node_type in ("lexical_declaration", "variable_declaration"):
            visibility = self._extract_visibility(node, source_text, is_exported)

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
                        params = self._extract_parameters(value_node, source_text)
                        ret_type = self._extract_return_type(value_node, source_text)

                        symbols.append(
                            SymbolItem(
                                name=func_name,
                                kind=kind,
                                file_path=relative_path,
                                line_start=node.start_point[0] + 1,
                                line_end=node.end_point[0] + 1,
                                signature=signature,
                                docstring=docstring,
                                parent_symbol=parent_class,
                                parameters=params,
                                return_type=ret_type,
                                visibility=visibility,
                            )
                        )
            return

        # Traverse general children
        for child in node.children:
            self._traverse_node(child, source_text, relative_path, symbols, class_stack, is_exported)

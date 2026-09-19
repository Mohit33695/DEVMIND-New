"""
Tree-sitter Java Symbol Parser.

Purpose:
Statically inspects Java (.java) source files using Tree-sitter concrete syntax tree (CST) parsing.
Extracts functions, classes, interfaces, constructors, methods, and imports without executing code.
"""

import logging
import os
from typing import List, Optional

from tree_sitter import Language, Node, Parser
import tree_sitter_java

from app.schemas.symbols import SymbolItem, SymbolKind
from app.services.parser.base import BaseLanguageParser

logger = logging.getLogger(__name__)


class JavaTreeSitterParser(BaseLanguageParser):
    """Static Tree-sitter symbol parser for Java source files."""

    def __init__(self):
        self._java_lang = Language(tree_sitter_java.language())

    def _clean_docstring(self, raw_comment: str) -> Optional[str]:
        """Cleans Java Javadoc/comment blocks into readable docstrings."""
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
        if prev and prev.type in ("block_comment", "line_comment"):
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
        Statically parses a Java file into Tree-sitter CST nodes and extracts symbols.
        Returns an empty list gracefully on reading or unhandled errors.
        """
        try:
            with open(file_path, "rb") as f:
                source_bytes = f.read()

            source_text = source_bytes.decode("utf-8", errors="replace")
            parser = Parser(self._java_lang)

            tree = parser.parse(source_bytes)
            symbols: List[SymbolItem] = []

            self._traverse_node(tree.root_node, source_text, relative_path, symbols)
            return symbols
        except Exception as exc:
            logger.warning(f"Failed to parse symbols in '{relative_path}': {str(exc)}")
            return []

    def _extract_parameters(self, node: Node, source_text: str) -> Optional[List[str]]:
        """Extracts formal parameter names from a Java method or constructor node."""
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            return None
        param_names = []
        for child in params_node.children:
            if child.type == "formal_parameter":
                name_node = child.child_by_field_name("name")
                if name_node:
                    param_names.append(self._get_node_text(name_node, source_text).strip())
                else:
                    text = self._get_node_text(child, source_text).strip()
                    if text and text not in ("(", ")", ","):
                        param_names.append(text.split()[-1])
        return param_names if param_names else None

    def _extract_return_type(self, node: Node, source_text: str) -> Optional[str]:
        """Extracts return type from a Java method node."""
        type_node = node.child_by_field_name("type")
        if type_node:
            return self._get_node_text(type_node, source_text).strip()
        return None

    def _extract_visibility(self, node: Node, source_text: str) -> Optional[str]:
        """Extracts Java visibility modifier (public/private/protected) if explicitly present."""
        for child in node.children:
            if child.type == "modifiers":
                text = self._get_node_text(child, source_text)
                tokens = text.split()
                if "public" in tokens:
                    return "public"
                elif "private" in tokens:
                    return "private"
                elif "protected" in tokens:
                    return "protected"
        return None

    def _traverse_node(
        self,
        node: Node,
        source_text: str,
        relative_path: str,
        symbols: List[SymbolItem],
        class_stack: Optional[List[str]] = None,
    ):
        """Recursively traverses Tree-sitter CST nodes to extract Java symbols."""
        if class_stack is None:
            class_stack = []

        node_type = node.type
        parent_class = class_stack[-1] if class_stack else None

        # 1. Imports
        if node_type == "import_declaration":
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

        # 2. Classes & Interfaces
        elif node_type in ("class_declaration", "interface_declaration"):
            name_node = node.child_by_field_name("name")
            class_name = (
                self._get_node_text(name_node, source_text)
                if name_node
                else "AnonymousClass"
            )
            signature = self._get_signature(node, source_text)
            docstring = self._get_docstring(node, source_text)
            visibility = self._extract_visibility(node, source_text)

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

            # Traverse class/interface body for methods and constructors
            body_node = node.child_by_field_name("body")
            if body_node:
                new_class_stack = class_stack + [class_name]
                for child in body_node.children:
                    self._traverse_node(
                        child, source_text, relative_path, symbols, new_class_stack
                    )
            return

        # 3. Constructors & Methods
        elif node_type in ("constructor_declaration", "method_declaration"):
            name_node = node.child_by_field_name("name")
            method_name = (
                self._get_node_text(name_node, source_text)
                if name_node
                else "method"
            )
            signature = self._get_signature(node, source_text)
            docstring = self._get_docstring(node, source_text)
            params = self._extract_parameters(node, source_text)
            ret_type = self._extract_return_type(node, source_text) if node_type == "method_declaration" else None
            visibility = self._extract_visibility(node, source_text)

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

        # Traverse general children
        for child in node.children:
            self._traverse_node(child, source_text, relative_path, symbols, class_stack)

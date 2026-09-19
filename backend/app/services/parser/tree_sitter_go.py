"""
Tree-sitter Go Symbol Parser.

Purpose:
Statically inspects Go (.go) source files using Tree-sitter concrete syntax tree (CST) parsing.
Extracts functions, receiver methods, struct types, interface types, and imports without executing code.
"""

import logging
import os
from typing import List, Optional

from tree_sitter import Language, Node, Parser
import tree_sitter_go

from app.schemas.symbols import SymbolItem, SymbolKind
from app.services.parser.base import BaseLanguageParser

logger = logging.getLogger(__name__)


class GoTreeSitterParser(BaseLanguageParser):
    """Static Tree-sitter symbol parser for Go source files."""

    def __init__(self):
        self._go_lang = Language(tree_sitter_go.language())

    def _clean_docstring(self, raw_comment: str) -> Optional[str]:
        """Cleans Go comment blocks into readable docstrings."""
        if not raw_comment:
            return None
        lines = raw_comment.strip().splitlines()
        cleaned_lines = []
        for line in lines:
            l = line.strip()
            if l.startswith("/*"):
                l = l[2:].strip()
            if l.endswith("*/"):
                l = l[:-2].strip()
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
        if first_line.endswith("{"):
            first_line = first_line[:-1].strip()
        return first_line

    def parse_file(self, file_path: str, relative_path: str) -> List[SymbolItem]:
        """
        Statically parses a Go file into Tree-sitter CST nodes and extracts symbols.
        Returns an empty list gracefully on reading or unhandled errors.
        """
        try:
            with open(file_path, "rb") as f:
                source_bytes = f.read()

            source_text = source_bytes.decode("utf-8", errors="replace")
            parser = Parser(self._go_lang)

            tree = parser.parse(source_bytes)
            symbols: List[SymbolItem] = []

            self._traverse_node(tree.root_node, source_text, relative_path, symbols)
            return symbols
        except Exception as exc:
            logger.warning(f"Failed to parse symbols in '{relative_path}': {str(exc)}")
            return []

    def _extract_receiver_parent(self, node: Node, source_text: str) -> Optional[str]:
        """Extracts parent type name for Go receiver methods."""
        recv_node = node.child_by_field_name("receiver")
        if not recv_node:
            return None
        text = self._get_node_text(recv_node, source_text).strip()
        cleaned = text.strip("()").split()
        if cleaned:
            raw_type = cleaned[-1].lstrip("*")
            return raw_type if raw_type else None
        return None

    def _extract_parameters(self, node: Node, source_text: str) -> Optional[List[str]]:
        """Extracts formal parameter names from a Go function or method node."""
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            return None
        param_names = []
        for child in params_node.children:
            if child.type == "parameter_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    param_names.append(self._get_node_text(name_node, source_text).strip())
                else:
                    text = self._get_node_text(child, source_text).strip()
                    if text and text not in ("(", ")", ","):
                        param_names.append(text.split()[0])
        return param_names if param_names else None

    def _extract_return_type(self, node: Node, source_text: str) -> Optional[str]:
        """Extracts return type string from a Go function or method node."""
        res_node = node.child_by_field_name("result")
        if res_node:
            text = self._get_node_text(res_node, source_text).strip()
            if text.startswith("(") and text.endswith(")"):
                text = text[1:-1].strip()
            return text if text else None
        return None

    def _extract_visibility(self, name: str) -> Optional[str]:
        """Determines Go export visibility based on identifier capitalization."""
        if not name:
            return None
        return "export" if name[0].isupper() else "package"

    def _traverse_node(
        self,
        node: Node,
        source_text: str,
        relative_path: str,
        symbols: List[SymbolItem],
    ):
        """Recursively traverses Tree-sitter CST nodes to extract Go symbols."""
        node_type = node.type

        # 1. Imports (single or grouped)
        if node_type == "import_declaration":
            # Check for grouped imports: import_spec_list -> import_spec
            spec_list = [c for c in node.children if c.type == "import_spec_list"]
            if spec_list:
                for spec in spec_list[0].children:
                    if spec.type == "import_spec":
                        path_text = self._get_node_text(spec, source_text).strip()
                        import_stmt = f"import {path_text}"
                        symbols.append(
                            SymbolItem(
                                name=import_stmt,
                                kind=SymbolKind.IMPORT,
                                file_path=relative_path,
                                line_start=spec.start_point[0] + 1,
                                line_end=spec.end_point[0] + 1,
                                signature=import_stmt,
                                docstring=None,
                                parent_symbol=None,
                                parameters=None,
                                return_type=None,
                                visibility=None,
                            )
                        )
            else:
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

        # 2. Standalone Functions
        elif node_type == "function_declaration":
            name_node = node.child_by_field_name("name")
            func_name = (
                self._get_node_text(name_node, source_text)
                if name_node
                else "function"
            )
            signature = self._get_signature(node, source_text)
            docstring = self._get_docstring(node, source_text)
            params = self._extract_parameters(node, source_text)
            ret_type = self._extract_return_type(node, source_text)
            visibility = self._extract_visibility(func_name)

            symbols.append(
                SymbolItem(
                    name=func_name,
                    kind=SymbolKind.FUNCTION,
                    file_path=relative_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=signature,
                    docstring=docstring,
                    parent_symbol=None,
                    parameters=params,
                    return_type=ret_type,
                    visibility=visibility,
                )
            )
            return

        # 3. Receiver Methods
        elif node_type == "method_declaration":
            name_node = node.child_by_field_name("name")
            method_name = (
                self._get_node_text(name_node, source_text)
                if name_node
                else "method"
            )
            signature = self._get_signature(node, source_text)
            docstring = self._get_docstring(node, source_text)
            parent_type = self._extract_receiver_parent(node, source_text)
            params = self._extract_parameters(node, source_text)
            ret_type = self._extract_return_type(node, source_text)
            visibility = self._extract_visibility(method_name)

            symbols.append(
                SymbolItem(
                    name=method_name,
                    kind=SymbolKind.METHOD,
                    file_path=relative_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=signature,
                    docstring=docstring,
                    parent_symbol=parent_type,
                    parameters=params,
                    return_type=ret_type,
                    visibility=visibility,
                )
            )
            return

        # 4. Struct & Interface Types
        elif node_type == "type_declaration":
            docstring = self._get_docstring(node, source_text)
            for child in node.children:
                if child.type == "type_spec":
                    name_node = child.child_by_field_name("name")
                    type_node = child.child_by_field_name("type")

                    if name_node and type_node and type_node.type in ("struct_type", "interface_type"):
                        type_name = self._get_node_text(name_node, source_text)
                        signature = self._get_signature(child, source_text)
                        visibility = self._extract_visibility(type_name)

                        symbols.append(
                            SymbolItem(
                                name=type_name,
                                kind=SymbolKind.CLASS,
                                file_path=relative_path,
                                line_start=child.start_point[0] + 1,
                                line_end=child.end_point[0] + 1,
                                signature=f"type {signature}",
                                docstring=docstring,
                                parent_symbol=None,
                                parameters=None,
                                return_type=None,
                                visibility=visibility,
                            )
                        )
            return

        # Traverse general children
        for child in node.children:
            self._traverse_node(child, source_text, relative_path, symbols)

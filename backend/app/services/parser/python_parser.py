"""
Static Python AST Symbol Parser.

Purpose:
Statically inspects Python (.py) source files using Python's native `ast` module.
Extracts functions, async functions, classes, methods, and imports without executing code.
"""

import ast
import logging
from typing import List, Optional

from app.schemas.symbols import SymbolItem, SymbolKind
from app.services.parser.base import BaseLanguageParser

logger = logging.getLogger(__name__)


class PythonASTVisitor(ast.NodeVisitor):
    """AST NodeVisitor to extract symbols from parsed Python AST trees."""

    def __init__(self, relative_path: str):
        self.relative_path = relative_path
        self.symbols: List[SymbolItem] = []
        self._class_stack: List[str] = []

    def _get_node_end_line(self, node: ast.AST) -> int:
        """Returns end line number if available, falling back to lineno."""
        return getattr(node, "end_lineno", getattr(node, "lineno", 1))

    def visit_Import(self, node: ast.Import):
        names = ", ".join(alias.name for alias in node.names)
        import_stmt = f"import {names}"
        self.symbols.append(
            SymbolItem(
                name=import_stmt,
                kind=SymbolKind.IMPORT,
                file_path=self.relative_path,
                line_start=node.lineno,
                line_end=self._get_node_end_line(node),
                signature=import_stmt,
                docstring=None,
            )
        )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        dots = "." * (node.level or 0)
        module = node.module or ""
        names = ", ".join(alias.name for alias in node.names)
        import_stmt = f"from {dots}{module} import {names}" if (module or dots) else f"import {names}"
        self.symbols.append(
            SymbolItem(
                name=import_stmt,
                kind=SymbolKind.IMPORT,
                file_path=self.relative_path,
                line_start=node.lineno,
                line_end=self._get_node_end_line(node),
                signature=import_stmt,
                docstring=None,
            )
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        base_names = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_names.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_names.append(f"{getattr(base.value, 'id', '')}.{base.attr}")

        bases_str = f"({', '.join(base_names)})" if base_names else ""
        signature = f"class {node.name}{bases_str}"
        docstring = ast.get_docstring(node)

        visibility = "private" if (node.name.startswith("_") and not node.name.startswith("__")) else "public"

        self.symbols.append(
            SymbolItem(
                name=node.name,
                kind=SymbolKind.CLASS,
                file_path=self.relative_path,
                line_start=node.lineno,
                line_end=self._get_node_end_line(node),
                signature=signature,
                docstring=docstring,
                parent_symbol=None,
                parameters=None,
                return_type=None,
                visibility=visibility,
            )
        )

        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def _visit_function(self, node: ast.AST, is_async: bool = False):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return

        is_method = len(self._class_stack) > 0
        kind = SymbolKind.METHOD if is_method else SymbolKind.FUNCTION
        parent_symbol = self._class_stack[-1] if is_method else None

        # Format function parameters safely
        param_names = [arg.arg for arg in node.args.args]
        if node.args.vararg:
            param_names.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            param_names.append(f"**{node.args.kwarg.arg}")

        prefix = "async def" if is_async else "def"
        signature = f"{prefix} {node.name}({', '.join(param_names)})"
        docstring = ast.get_docstring(node)

        return_type = None
        if node.returns:
            try:
                return_type = ast.unparse(node.returns)
            except Exception:
                return_type = None

        visibility = "private" if (node.name.startswith("_") and not node.name.startswith("__")) else "public"

        self.symbols.append(
            SymbolItem(
                name=node.name,
                kind=kind,
                file_path=self.relative_path,
                line_start=node.lineno,
                line_end=self._get_node_end_line(node),
                signature=signature,
                docstring=docstring,
                parent_symbol=parent_symbol,
                parameters=param_names if param_names else None,
                return_type=return_type,
                visibility=visibility,
            )
        )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_function(node, is_async=True)


class PythonParser(BaseLanguageParser):
    """Static Python source code AST parser implementation."""

    def parse_file(self, file_path: str, relative_path: str) -> List[SymbolItem]:
        """
        Statically parses a Python source file into AST nodes and extracts symbols.

        Returns an empty list gracefully if the file contains syntax errors or unreadable encoding.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            parsed_ast = ast.parse(content, filename=relative_path)
            visitor = PythonASTVisitor(relative_path)
            visitor.visit(parsed_ast)
            return visitor.symbols
        except SyntaxError as e:
            logger.warning(
                f"Skipping symbol parsing for '{relative_path}': Syntax error at line {e.lineno}"
            )
            return []
        except Exception as exc:
            logger.warning(f"Failed to parse symbols in '{relative_path}': {str(exc)}")
            return []

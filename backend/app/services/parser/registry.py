"""
Parser Registry for Multi-Language Code Intelligence.

Purpose:
Maps file extensions to appropriate language symbol parsers.
- Python (.py) uses native Python AST (PythonParser).
- JS/JSX/TS/TSX use Tree-sitter (TypeScriptTreeSitterParser).
- All parsers produce the same unified SymbolItem model.
"""

import os
from typing import Dict, Optional

from app.services.parser.base import BaseLanguageParser
from app.services.parser.python_parser import PythonParser
from app.services.parser.tree_sitter_go import GoTreeSitterParser
from app.services.parser.tree_sitter_java import JavaTreeSitterParser
from app.services.parser.tree_sitter_ts import TypeScriptTreeSitterParser


class ParserRegistry:
    """Registry responsible for mapping file extensions to parser instances."""

    def __init__(self):
        self._python_parser = PythonParser()
        self._ts_parser = TypeScriptTreeSitterParser()
        self._java_parser = JavaTreeSitterParser()
        self._go_parser = GoTreeSitterParser()

        self._registry: Dict[str, BaseLanguageParser] = {
            ".py": self._python_parser,
            ".js": self._ts_parser,
            ".jsx": self._ts_parser,
            ".ts": self._ts_parser,
            ".tsx": self._ts_parser,
            ".java": self._java_parser,
            ".go": self._go_parser,
        }

    def get_parser_for_file(self, file_path: str) -> Optional[BaseLanguageParser]:
        """
        Returns the appropriate parser for a given file path based on extension.
        Returns None for unsupported file types.
        """
        if not file_path:
            return None
        _, ext = os.path.splitext(file_path.lower())
        return self._registry.get(ext)

    def is_supported_file(self, file_path: str) -> bool:
        """Checks if a file extension has a registered parser."""
        return self.get_parser_for_file(file_path) is not None

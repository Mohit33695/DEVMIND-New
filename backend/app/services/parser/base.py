"""
Abstract base parser interface for static code intelligence.
"""

from abc import ABC, abstractmethod
from typing import List

from app.schemas.symbols import SymbolItem


class BaseLanguageParser(ABC):
    """Abstract interface for static source code symbol parsers."""

    @abstractmethod
    def parse_file(self, file_path: str, relative_path: str) -> List[SymbolItem]:
        """
        Statically parses a source code file and extracts code symbols.

        Args:
            file_path: Absolute path to the source file on disk.
            relative_path: Relative path of the file inside the repository.

        Returns:
            List[SymbolItem]: Extracted functions, classes, methods, and imports.
        """
        pass

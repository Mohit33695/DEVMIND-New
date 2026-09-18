"""
Unit tests for PythonASTParser static code symbol extraction.
"""

import os
import tempfile
from app.schemas.symbols import SymbolKind
from app.services.parser.python_parser import PythonParser


def test_python_parser_extracts_symbols():
    """Verifies static extraction of functions, async functions, classes, methods, and imports."""
    sample_code = '''"""Sample module docstring."""
import os
from typing import List, Optional

class UserAccount:
    """User account model class."""

    def __init__(self, username: str):
        """Initialize user account."""
        self.username = username

    async def fetch_profile(self) -> dict:
        """Fetch user profile asynchronously."""
        return {"user": self.username}


def top_level_function(a, b):
    """Top level helper function."""
    return a + b


async def async_worker():
    """Async worker function."""
    pass
'''

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(sample_code)
        temp_file_path = temp_file.name

    try:
        parser = PythonParser()
        symbols = parser.parse_file(temp_file_path, "sample.py")

        # 1. Imports
        import_symbols = [s for s in symbols if s.kind == SymbolKind.IMPORT]
        assert len(import_symbols) == 2
        assert "import os" in [s.name for s in import_symbols]
        assert "from typing import List, Optional" in [s.name for s in import_symbols]

        # 2. Classes
        class_symbols = [s for s in symbols if s.kind == SymbolKind.CLASS]
        assert len(class_symbols) == 1
        assert class_symbols[0].name == "UserAccount"
        assert class_symbols[0].docstring == "User account model class."
        assert class_symbols[0].signature == "class UserAccount"

        # 3. Methods inside class
        method_symbols = [s for s in symbols if s.kind == SymbolKind.METHOD]
        assert len(method_symbols) == 2
        method_names = [m.name for m in method_symbols]
        assert "__init__" in method_names
        assert "fetch_profile" in method_names

        # Verify async method signature prefix
        fetch_method = next(m for m in method_symbols if m.name == "fetch_profile")
        assert "async def fetch_profile" in fetch_method.signature

        # 4. Top level functions
        func_symbols = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
        assert len(func_symbols) == 2
        func_names = [f.name for f in func_symbols]
        assert "top_level_function" in func_names
        assert "async_worker" in func_names

        # 5. Line numbers check
        for s in symbols:
            assert s.line_start >= 1
            assert s.line_end >= s.line_start
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def test_python_parser_syntax_error_handling():
    """Verifies that PythonParser handles invalid Python syntax gracefully without crashing."""
    invalid_code = "def broken_func(:\n    invalid syntax here!"

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(invalid_code)
        temp_file_path = temp_file.name

    try:
        parser = PythonParser()
        symbols = parser.parse_file(temp_file_path, "invalid.py")
        assert symbols == []
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

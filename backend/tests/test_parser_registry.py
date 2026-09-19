"""
Unit tests for ParserRegistry extension mapping.
"""

from app.services.parser.python_parser import PythonParser
from app.services.parser.registry import ParserRegistry
from app.services.parser.tree_sitter_go import GoTreeSitterParser
from app.services.parser.tree_sitter_java import JavaTreeSitterParser
from app.services.parser.tree_sitter_ts import TypeScriptTreeSitterParser


def test_parser_registry_extension_mapping():
    """Verifies that ParserRegistry correctly returns appropriate parser instances based on file extensions."""
    registry = ParserRegistry()

    # 1. Python
    py_parser = registry.get_parser_for_file("app/main.py")
    assert py_parser is not None
    assert isinstance(py_parser, PythonParser)

    # 2. JavaScript / JSX
    js_parser = registry.get_parser_for_file("src/index.js")
    assert js_parser is not None
    assert isinstance(js_parser, TypeScriptTreeSitterParser)

    jsx_parser = registry.get_parser_for_file("src/App.jsx")
    assert jsx_parser is not None
    assert isinstance(jsx_parser, TypeScriptTreeSitterParser)

    # 3. TypeScript / TSX
    ts_parser = registry.get_parser_for_file("src/types.ts")
    assert ts_parser is not None
    assert isinstance(ts_parser, TypeScriptTreeSitterParser)

    tsx_parser = registry.get_parser_for_file("src/Component.tsx")
    assert tsx_parser is not None
    assert isinstance(tsx_parser, TypeScriptTreeSitterParser)

    # 4. Java
    java_parser = registry.get_parser_for_file("src/Server.java")
    assert java_parser is not None
    assert isinstance(java_parser, JavaTreeSitterParser)

    # 5. Go
    go_parser = registry.get_parser_for_file("src/main.go")
    assert go_parser is not None
    assert isinstance(go_parser, GoTreeSitterParser)

    # 6. Unsupported extensions return None
    assert registry.get_parser_for_file("README.md") is None
    assert registry.get_parser_for_file("data.json") is None
    assert registry.get_parser_for_file("binary.bin") is None
    assert registry.get_parser_for_file("") is None

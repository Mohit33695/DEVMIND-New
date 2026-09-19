"""
Unit tests for JavaTreeSitterParser static symbol extraction.
"""

import os
import tempfile
from app.schemas.symbols import SymbolKind
from app.services.parser.tree_sitter_java import JavaTreeSitterParser


def _parse_java_snippet(code: str):
    """Helper to parse a Java code snippet with temporary file."""
    with tempfile.NamedTemporaryFile("w", suffix=".java", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        parser = JavaTreeSitterParser()
        return parser.parse_file(temp_file_path, "Server.java")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def test_java_symbol_extraction():
    """Verifies static extraction of Java imports, classes, interfaces, constructors, and methods."""
    java_code = """package com.devmind;

import java.util.List;
import java.util.Map;

/**
 * Main application Server class.
 */
public class Server {
    private int port;

    /**
     * Constructor for Server.
     */
    public Server(int port) {
        this.port = port;
    }

    /**
     * Start the server instance.
     */
    public void start() {
    }
}

/**
 * Repository interface abstraction.
 */
public interface Repository {
    void save(Object entity);
}
"""

    symbols = _parse_java_snippet(java_code)

    # 1. Imports
    imports = [s for s in symbols if s.kind == SymbolKind.IMPORT]
    assert len(imports) == 2
    import_sigs = [s.signature for s in imports]
    assert "import java.util.List" in import_sigs
    assert "import java.util.Map" in import_sigs

    # 2. Classes & Interfaces
    classes = [s for s in symbols if s.kind == SymbolKind.CLASS]
    assert len(classes) == 2
    class_names = [c.name for c in classes]
    assert "Server" in class_names
    assert "Repository" in class_names

    server_class = next(c for c in classes if c.name == "Server")
    assert server_class.docstring == "Main application Server class."

    repo_interface = next(c for c in classes if c.name == "Repository")
    assert repo_interface.docstring == "Repository interface abstraction."

    # 3. Constructors & Methods
    methods = [s for s in symbols if s.kind == SymbolKind.METHOD]
    method_names = [m.name for m in methods]
    assert "Server" in method_names
    assert "start" in method_names
    assert "save" in method_names

    constructor_symbol = next(m for m in methods if m.name == "Server")
    assert constructor_symbol.docstring == "Constructor for Server."

    start_method = next(m for m in methods if m.name == "start")
    assert start_method.docstring == "Start the server instance."

    # Line number check
    for s in symbols:
        assert s.line_start >= 1
        assert s.line_end >= s.line_start


def test_java_malformed_source_handling():
    """Verifies graceful error tolerance on malformed Java code."""
    broken_java = """public class BrokenServer {
    public void start( {
        // syntax error
"""

    symbols = _parse_java_snippet(broken_java)
    assert isinstance(symbols, list)


def test_java_empty_source_handling():
    """Verifies empty Java source returns empty symbol list."""
    symbols = _parse_java_snippet("")
    assert symbols == []

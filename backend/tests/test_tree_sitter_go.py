"""
Unit tests for GoTreeSitterParser static symbol extraction.
"""

import os
import tempfile
from app.schemas.symbols import SymbolKind
from app.services.parser.tree_sitter_go import GoTreeSitterParser


def _parse_go_snippet(code: str):
    """Helper to parse a Go code snippet with temporary file."""
    with tempfile.NamedTemporaryFile("w", suffix=".go", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        parser = GoTreeSitterParser()
        return parser.parse_file(temp_file_path, "main.go")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def test_go_symbol_extraction():
    """Verifies static extraction of Go single/grouped imports, functions, receiver methods, structs, and interfaces."""
    go_code = """package main

import "fmt"
import (
    "net/http"
    "os"
)

// Server configuration struct.
type Server struct {
    Port int
}

// Runner interface contract.
type Runner interface {
    Run() error
}

// Top-level factory function.
func NewServer(port int) *Server {
    return &Server{Port: port}
}

// Receiver method for Server.
func (s *Server) Start() error {
    fmt.Println("Server running on port", s.Port)
    return nil
}
"""

    symbols = _parse_go_snippet(go_code)

    # 1. Imports (single and grouped)
    imports = [s for s in symbols if s.kind == SymbolKind.IMPORT]
    assert len(imports) == 3
    import_names = [s.name for s in imports]
    assert 'import "fmt"' in import_names
    assert 'import "net/http"' in import_names
    assert 'import "os"' in import_names

    # 2. Structs & Interfaces (mapped to CLASS)
    classes = [s for s in symbols if s.kind == SymbolKind.CLASS]
    assert len(classes) == 2
    class_names = [c.name for c in classes]
    assert "Server" in class_names
    assert "Runner" in class_names

    server_struct = next(c for c in classes if c.name == "Server")
    assert server_struct.docstring == "Server configuration struct."

    runner_interface = next(c for c in classes if c.name == "Runner")
    assert runner_interface.docstring == "Runner interface contract."

    # 3. Standalone Functions
    funcs = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
    assert len(funcs) == 1
    assert funcs[0].name == "NewServer"
    assert funcs[0].docstring == "Top-level factory function."

    # 4. Receiver Methods
    methods = [s for s in symbols if s.kind == SymbolKind.METHOD]
    assert len(methods) == 1
    assert methods[0].name == "Start"
    assert methods[0].docstring == "Receiver method for Server."
    assert "func (s *Server) Start() error" in methods[0].signature

    # Line number check
    for s in symbols:
        assert s.line_start >= 1
        assert s.line_end >= s.line_start


def test_go_malformed_source_handling():
    """Verifies graceful error tolerance on malformed Go code."""
    broken_go = """package main

func BrokenFunc( {
    invalid syntax
"""

    symbols = _parse_go_snippet(broken_go)
    assert isinstance(symbols, list)


def test_go_empty_source_handling():
    """Verifies empty Go source returns empty symbol list."""
    symbols = _parse_go_snippet("")
    assert symbols == []

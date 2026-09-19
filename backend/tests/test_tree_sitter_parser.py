"""
Unit tests for TypeScriptTreeSitterParser static symbol extraction.
"""

import os
import tempfile
from app.schemas.symbols import SymbolKind
from app.services.parser.tree_sitter_ts import TypeScriptTreeSitterParser


def _parse_snippet(code: str, extension: str):
    """Helper to parse a code string snippet with temporary file."""
    with tempfile.NamedTemporaryFile("w", suffix=extension, delete=False, encoding="utf-8") as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        parser = TypeScriptTreeSitterParser()
        return parser.parse_file(temp_file_path, f"sample{extension}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def test_javascript_symbol_extraction():
    """Verifies symbol extraction for JavaScript functions, async functions, classes, methods, and imports."""
    js_code = """/**
 * Main application logger import.
 */
import logger from './logger';
import { formatDate } from './utils';

/**
 * User Account class.
 */
class UserAccount {
  constructor(name) {
    this.name = name;
  }

  /**
   * Fetch user data asynchronously.
   */
  async fetchProfile() {
    return { name: this.name };
  }
}

/**
 * Top-level helper function.
 */
function topLevelFunc(a, b) {
  return a + b;
}

/**
 * Arrow function declaration.
 */
const asyncArrow = async (x) => {
  return x * 2;
};
"""

    symbols = _parse_snippet(js_code, ".js")

    # 1. Imports
    imports = [s for s in symbols if s.kind == SymbolKind.IMPORT]
    assert len(imports) == 2
    assert "import logger from './logger'" in [s.signature for s in imports]
    assert "import { formatDate } from './utils'" in [s.signature for s in imports]

    # 2. Classes
    classes = [s for s in symbols if s.kind == SymbolKind.CLASS]
    assert len(classes) == 1
    assert classes[0].name == "UserAccount"
    assert classes[0].docstring == "User Account class."

    # 3. Methods
    methods = [s for s in symbols if s.kind == SymbolKind.METHOD]
    assert len(methods) == 2
    method_names = [m.name for m in methods]
    assert "constructor" in method_names
    assert "fetchProfile" in method_names

    fetch_method = next(m for m in methods if m.name == "fetchProfile")
    assert fetch_method.docstring == "Fetch user data asynchronously."

    # 4. Functions
    funcs = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
    func_names = [f.name for f in funcs]
    assert "topLevelFunc" in func_names
    assert "asyncArrow" in func_names


def test_typescript_symbol_extraction():
    """Verifies symbol extraction for TypeScript & TSX constructs."""
    ts_code = """import React from 'react';
import type { User } from './types';

export class DataService<T> {
  private data: T;

  constructor(initialData: T) {
    this.data = initialData;
  }

  public async getData(): Promise<T> {
    return this.data;
  }
}

export function processUser(user: User): boolean {
  return user.id > 0;
}

export const renderButton = (label: string): JSX.Element => {
  return <button>{label}</button>;
};
"""

    symbols = _parse_snippet(ts_code, ".tsx")

    # 1. Imports
    imports = [s for s in symbols if s.kind == SymbolKind.IMPORT]
    assert len(imports) == 2

    # 2. Classes
    classes = [s for s in symbols if s.kind == SymbolKind.CLASS]
    assert len(classes) == 1
    assert classes[0].name == "DataService"

    # 3. Methods
    methods = [s for s in symbols if s.kind == SymbolKind.METHOD]
    assert len(methods) == 2
    method_names = [m.name for m in methods]
    assert "constructor" in method_names
    assert "getData" in method_names

    # 4. Functions
    funcs = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
    func_names = [f.name for f in funcs]
    assert "processUser" in func_names
    assert "renderButton" in func_names


def test_malformed_source_handling():
    """Verifies that Tree-sitter handles malformed source code gracefully without crashing."""
    broken_code = """function brokenFunction(x {
  const y = 10;
  return y;
"""

    symbols = _parse_snippet(broken_code, ".js")
    # Tree-sitter extracts partial symbols or returns without crashing
    assert isinstance(symbols, list)


def test_empty_source_handling():
    """Verifies parsing empty source files returns empty list."""
    symbols = _parse_snippet("", ".ts")
    assert symbols == []

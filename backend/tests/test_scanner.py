"""
Unit tests for RepositoryScanner service and Zip Slip path traversal security.
"""

import io
import zipfile
import pytest

from app.services.scanner import RepositoryScanner, ZipPathTraversalError


def create_in_memory_zip(files_map: dict) -> bytes:
    """Helper utility to create a zip file buffer from a dictionary of filename -> content."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_map.items():
            zf.writestr(filename, content)
    return buffer.getvalue()


def test_scan_zip_file_valid():
    """Tests scanning a valid repository ZIP with multi-language files and ignored directories."""
    files = {
        "src/index.ts": "console.log('hello');",
        "src/App.tsx": "export const App = () => <div>Hello</div>;",
        "backend/main.py": "print('hello')",
        "backend/utils.py": "def add(a, b): return a + b",
        "README.md": "# Title",
        "Dockerfile": "FROM python:3.11",
        # Ignored files/directories:
        "node_modules/express/index.js": "module.exports = {};",
        ".git/config": "[core]\nrepositoryformatversion = 0",
        "dist/bundle.js": "var bundle = true;",
        "build/output.js": "var output = true;",
        "venv/lib/python.py": "# virtualenv",
        ".venv/lib/python.py": "# virtualenv",
    }

    zip_bytes = create_in_memory_zip(files)
    result = RepositoryScanner.scan_zip_file(zip_bytes)

    # 6 valid files should be counted (node_modules, .git, dist, build, venv, .venv excluded)
    assert result.total_files == 6
    assert result.detected_languages.get("TypeScript") == 1
    assert result.detected_languages.get("TypeScript React") == 1
    assert result.detected_languages.get("Python") == 2
    assert result.detected_languages.get("Markdown") == 1
    assert result.detected_languages.get("Docker") == 1

    # Verify ignored directories are not in scanned files or directories
    for path in result.scanned_files:
        assert not path.startswith("node_modules")
        assert not path.startswith(".git")
        assert not path.startswith("dist")
        assert not path.startswith("build")
        assert not path.startswith("venv")
        assert not path.startswith(".venv")

    assert "src" in result.directories
    assert "backend" in result.directories
    assert "node_modules" not in result.directories


def test_zip_path_traversal_protection():
    """Tests that ZIP archives containing path traversal entries (Zip Slip) raise ZipPathTraversalError."""
    malicious_files = {
        "normal.py": "print('ok')",
        "../evil.txt": "hacked",
    }

    zip_bytes = create_in_memory_zip(malicious_files)

    with pytest.raises(ZipPathTraversalError) as exc_info:
        RepositoryScanner.scan_zip_file(zip_bytes)

    assert "path traversal" in str(exc_info.value).lower()


def test_detect_language():
    """Tests language detection logic for various file extensions."""
    assert RepositoryScanner.detect_language("script.py") == "Python"
    assert RepositoryScanner.detect_language("app.tsx") == "TypeScript React"
    assert RepositoryScanner.detect_language("index.js") == "JavaScript"
    assert RepositoryScanner.detect_language("main.go") == "Go"
    assert RepositoryScanner.detect_language("lib.rs") == "Rust"
    assert RepositoryScanner.detect_language("Dockerfile") == "Docker"
    assert RepositoryScanner.detect_language("unknown.xyz") == "Other"

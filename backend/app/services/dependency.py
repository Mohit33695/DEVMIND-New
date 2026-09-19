"""
Repository Dependency Intelligence Service.

Purpose:
Statically analyzes code import dependencies across repository source files.
Determines internal, external, and unresolved module relationships.
Builds an internal dependency graph and detects circular dependency cycles.
"""

import os
import re
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.dependencies import (
    DependencyItem,
    DependencyType,
    RepositoryDependenciesResponse,
    ResolutionStatus,
)
from app.schemas.symbols import SymbolKind
from app.services.parser.service import CodeIntelligenceService
from app.services.scanner import RepositoryScanner
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService

# Python Standard Library Modules
PYTHON_STDLIB: Set[str] = {
    "abc", "argparse", "ast", "asyncio", "base64", "builtins", "collections",
    "concurrent", "contextlib", "copy", "csv", "dataclasses", "datetime",
    "decimal", "enum", "functools", "glob", "hashlib", "html", "http",
    "importlib", "inspect", "io", "itertools", "json", "logging", "math",
    "os", "pathlib", "pickle", "platform", "pprint", "random", "re",
    "shutil", "signal", "socket", "sqlite3", "ssl", "string", "struct",
    "subprocess", "sys", "tempfile", "threading", "time", "traceback",
    "typing", "typing_extensions", "unittest", "urllib", "uuid", "warnings",
    "weakref", "xml", "zipfile", "zlib"
}

# Python Popular External Packages
PYTHON_EXTERNAL: Set[str] = {
    "fastapi", "pydantic", "pytest", "requests", "numpy", "pandas", "scipy",
    "tree_sitter", "tree_sitter_javascript", "tree_sitter_typescript",
    "tree_sitter_java", "tree_sitter_go", "starlette", "httpx", "uvicorn",
    "jinja2", "click", "yaml", "toml", "sqlalchemy", "flask", "django"
}

# Node.js Standard Library Modules
JS_STDLIB: Set[str] = {
    "assert", "buffer", "child_process", "cluster", "crypto", "dgram",
    "dns", "domain", "events", "fs", "http", "https", "net", "os",
    "path", "punycode", "querystring", "readline", "stream", "string_decoder",
    "timers", "tls", "tty", "url", "util", "v8", "vm", "zlib"
}

# Go Standard Library Paths
GO_STDLIB: Set[str] = {
    "bufio", "bytes", "context", "crypto", "database/sql", "encoding",
    "encoding/json", "errors", "flag", "fmt", "html", "io", "log",
    "math", "net", "net/http", "os", "path", "path/filepath", "reflect",
    "regexp", "runtime", "sort", "strconv", "strings", "sync", "syscall",
    "testing", "time", "unicode", "unsafe"
}


class CodeDependencyService:
    """Stateless service analyzing module dependency relationships and cycle detection."""

    @classmethod
    def analyze_repository_dependencies(cls, repo_id: str) -> RepositoryDependenciesResponse:
        """
        Analyzes dependencies for all source files in a stored repository.

        Args:
            repo_id: Unique repository identifier.

        Returns:
            RepositoryDependenciesResponse: Extracted dependency metadata and detected cycles.

        Raises:
            RepositoryNotFoundError: If repository ID directory does not exist.
        """
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        # 1. Obtain repository scanned files & symbol extraction
        scan_result = RepositoryScanner.scan_extracted_directory(repo_dir)
        repo_files_set: Set[str] = set(scan_result.scanned_files)
        total_files = scan_result.total_files

        symbols_response = CodeIntelligenceService.extract_repository_symbols(repo_id)

        # 2. Extract and resolve all IMPORT symbols
        raw_items: List[DependencyItem] = []
        for file_symbols in symbols_response.file_symbols:
            source_file = file_symbols.file_path
            for sym in file_symbols.symbols:
                if sym.kind == SymbolKind.IMPORT:
                    parsed = cls._parse_and_resolve_import(
                        source_file=source_file,
                        raw_import=sym.signature or sym.name,
                        line_number=sym.line_start,
                        repo_files_set=repo_files_set,
                    )
                    if parsed:
                        raw_items.extend(parsed)

        # 3. Deduplicate and merge imported symbols for duplicate imports
        deduped_items = cls._deduplicate_dependencies(raw_items)

        # 4. Sort dependency items deterministically
        deduped_items.sort(
            key=lambda d: (
                d.source_file,
                d.line_number,
                d.module_name,
                d.target_file or "",
            )
        )

        # 5. Build internal adjacency graph and detect circular cycles
        adj_graph: Dict[str, Set[str]] = {}
        for item in deduped_items:
            if item.dependency_type == DependencyType.INTERNAL and item.target_file:
                if item.source_file != item.target_file:  # Exclude self-imports
                    adj_graph.setdefault(item.source_file, set()).add(item.target_file)

        cycles = cls._detect_circular_dependencies(adj_graph)

        # 6. Count metrics
        internal_count = sum(1 for d in deduped_items if d.dependency_type == DependencyType.INTERNAL and d.resolution_status == ResolutionStatus.RESOLVED)
        external_count = sum(1 for d in deduped_items if d.dependency_type == DependencyType.EXTERNAL)
        unresolved_count = sum(1 for d in deduped_items if d.resolution_status == ResolutionStatus.UNRESOLVED)

        return RepositoryDependenciesResponse(
            repo_id=repo_id,
            total_files=total_files,
            total_dependencies=len(deduped_items),
            internal_dependencies_count=internal_count,
            external_dependencies_count=external_count,
            unresolved_dependencies_count=unresolved_count,
            has_circular_dependencies=len(cycles) > 0,
            circular_dependency_cycles=cycles,
            dependencies=deduped_items,
        )

    @classmethod
    def _parse_and_resolve_import(
        cls,
        source_file: str,
        raw_import: str,
        line_number: int,
        repo_files_set: Set[str],
    ) -> List[DependencyItem]:
        """Routes import statement to language-specific parser & resolver."""
        _, ext = os.path.splitext(source_file.lower())

        if ext in (".py", ".pyw"):
            return cls._resolve_python_import(source_file, raw_import, line_number, repo_files_set)
        elif ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
            return cls._resolve_ts_js_import(source_file, raw_import, line_number, repo_files_set)
        elif ext == ".java":
            return cls._resolve_java_import(source_file, raw_import, line_number, repo_files_set)
        elif ext == ".go":
            return cls._resolve_go_import(source_file, raw_import, line_number, repo_files_set)

        return []

    # -------------------------------------------------------------------------
    # 1. PYTHON RESOLVER
    # -------------------------------------------------------------------------
    @classmethod
    def _resolve_python_import(
        cls,
        source_file: str,
        raw_import: str,
        line_number: int,
        repo_files_set: Set[str],
    ) -> List[DependencyItem]:
        results: List[DependencyItem] = []
        stmt = raw_import.strip()

        # Match `from .foo import bar` or `from foo import bar`
        from_match = re.match(r"^from\s+(\.*[A-Za-z0-9_\.]*)\s+import\s+(.+)$", stmt)
        if from_match:
            mod_part = from_match.group(1).strip()
            symbols_part = [s.strip().split()[0] for s in from_match.group(2).split(",") if s.strip()]

            target, dep_type, status = cls._resolve_python_module(source_file, mod_part, repo_files_set)
            results.append(
                DependencyItem(
                    source_file=source_file,
                    target_file=target,
                    raw_import=raw_import,
                    module_name=mod_part or ".",
                    imported_symbols=symbols_part,
                    dependency_type=dep_type,
                    resolution_status=status,
                    line_number=line_number,
                )
            )
            return results

        # Match `import foo, bar`
        import_match = re.match(r"^import\s+(.+)$", stmt)
        if import_match:
            modules = [m.strip().split()[0] for m in import_match.group(1).split(",") if m.strip()]
            for mod in modules:
                target, dep_type, status = cls._resolve_python_module(source_file, mod, repo_files_set)
                results.append(
                    DependencyItem(
                        source_file=source_file,
                        target_file=target,
                        raw_import=raw_import,
                        module_name=mod,
                        imported_symbols=[],
                        dependency_type=dep_type,
                        resolution_status=status,
                        line_number=line_number,
                    )
                )

        return results

    @classmethod
    def _resolve_python_module(
        cls,
        source_file: str,
        module_name: str,
        repo_files_set: Set[str],
    ) -> Tuple[Optional[str], DependencyType, ResolutionStatus]:
        if not module_name:
            return None, DependencyType.UNKNOWN, ResolutionStatus.UNRESOLVED

        # Handle relative imports (starting with .)
        if module_name.startswith("."):
            dots_count = len(module_name) - len(module_name.lstrip("."))
            rel_mod = module_name.lstrip(".")
            mod_path = rel_mod.replace(".", "/") if rel_mod else ""

            source_dir = os.path.dirname(source_file)
            base_dir = source_dir
            for _ in range(dots_count - 1):
                base_dir = os.path.dirname(base_dir)

            candidates = []
            if mod_path:
                candidates.append(os.path.normpath(os.path.join(base_dir, f"{mod_path}.py")).replace("\\", "/"))
                candidates.append(os.path.normpath(os.path.join(base_dir, mod_path, "__init__.py")).replace("\\", "/"))
            else:
                candidates.append(os.path.normpath(os.path.join(base_dir, "__init__.py")).replace("\\", "/"))

            for cand in candidates:
                if cand in repo_files_set:
                    return cand, DependencyType.INTERNAL, ResolutionStatus.RESOLVED

            return None, DependencyType.INTERNAL, ResolutionStatus.UNRESOLVED

        # Absolute import resolution
        mod_path = module_name.replace(".", "/")
        source_dir = os.path.dirname(source_file)

        candidates = [
            f"{mod_path}.py",
            f"{mod_path}/__init__.py",
            f"src/{mod_path}.py",
            f"src/{mod_path}/__init__.py",
            f"{source_dir}/{mod_path}.py",
            f"{source_dir}/{mod_path}/__init__.py",
        ]

        for cand in candidates:
            norm_cand = os.path.normpath(cand).replace("\\", "/")
            if norm_cand in repo_files_set:
                return norm_cand, DependencyType.INTERNAL, ResolutionStatus.RESOLVED

        # Stdlib or External checks
        top_module = module_name.split(".")[0]
        if top_module in PYTHON_STDLIB or top_module in PYTHON_EXTERNAL:
            return None, DependencyType.EXTERNAL, ResolutionStatus.EXTERNAL

        # If origin cannot be determined confidently
        return None, DependencyType.UNKNOWN, ResolutionStatus.UNRESOLVED

    # -------------------------------------------------------------------------
    # 2. JS / TS RESOLVER
    # -------------------------------------------------------------------------
    @classmethod
    def _resolve_ts_js_import(
        cls,
        source_file: str,
        raw_import: str,
        line_number: int,
        repo_files_set: Set[str],
    ) -> List[DependencyItem]:
        # Extract quoted module string: e.g. from './services' or require('../utils')
        match = re.search(r"['\"]([^'\"]+)['\"]", raw_import)
        if not match:
            return []

        module_specifier = match.group(1).strip()
        if not module_specifier:
            return []

        # Extract imported symbols if present
        imported_symbols: List[str] = []
        sym_match = re.search(r"\{([^}]+)\}", raw_import)
        if sym_match:
            imported_symbols = [s.strip().split(" as ")[0].strip() for s in sym_match.group(1).split(",") if s.strip()]

        target, dep_type, status = cls._resolve_ts_js_specifier(source_file, module_specifier, repo_files_set)

        return [
            DependencyItem(
                source_file=source_file,
                target_file=target,
                raw_import=raw_import,
                module_name=module_specifier,
                imported_symbols=imported_symbols,
                dependency_type=dep_type,
                resolution_status=status,
                line_number=line_number,
            )
        ]

    @classmethod
    def _resolve_ts_js_specifier(
        cls,
        source_file: str,
        specifier: str,
        repo_files_set: Set[str],
    ) -> Tuple[Optional[str], DependencyType, ResolutionStatus]:
        source_dir = os.path.dirname(source_file)
        has_src_dir = any(f.startswith("src/") for f in repo_files_set)

        # Handle `@/` alias
        norm_specifier = specifier
        if norm_specifier.startswith("@/"):
            norm_specifier = f"src/{norm_specifier[2:]}" if has_src_dir else f"./{norm_specifier[2:]}"

        is_relative = norm_specifier.startswith("./") or norm_specifier.startswith("../") or specifier.startswith("@/")

        if is_relative:
            base_path = os.path.normpath(os.path.join(source_dir, norm_specifier)).replace("\\", "/") if not norm_specifier.startswith("src/") else norm_specifier

            # Extension probing list
            probes = [
                base_path,
                f"{base_path}.ts",
                f"{base_path}.tsx",
                f"{base_path}.js",
                f"{base_path}.jsx",
                f"{base_path}/index.ts",
                f"{base_path}/index.tsx",
                f"{base_path}/index.js",
                f"{base_path}/index.jsx",
            ]

            for probe in probes:
                norm_probe = os.path.normpath(probe).replace("\\", "/")
                if norm_probe in repo_files_set:
                    return norm_probe, DependencyType.INTERNAL, ResolutionStatus.RESOLVED

            return None, DependencyType.INTERNAL, ResolutionStatus.UNRESOLVED

        # Package / Stdlib checks
        pkg_name = specifier.split("/")[0]
        if pkg_name in JS_STDLIB or not specifier.startswith("."):
            # Check if it resolves internally somewhere under src or root
            probes = [
                f"{specifier}.ts", f"{specifier}.tsx", f"{specifier}.js", f"{specifier}.jsx",
                f"src/{specifier}.ts", f"src/{specifier}.tsx", f"src/{specifier}.js", f"src/{specifier}.jsx",
            ]
            for probe in probes:
                norm_probe = os.path.normpath(probe).replace("\\", "/")
                if norm_probe in repo_files_set:
                    return norm_probe, DependencyType.INTERNAL, ResolutionStatus.RESOLVED

            if pkg_name in JS_STDLIB or not specifier.startswith((".", "/")):
                return None, DependencyType.EXTERNAL, ResolutionStatus.EXTERNAL

        return None, DependencyType.UNKNOWN, ResolutionStatus.UNRESOLVED

    # -------------------------------------------------------------------------
    # 3. JAVA RESOLVER
    # -------------------------------------------------------------------------
    @classmethod
    def _resolve_java_import(
        cls,
        source_file: str,
        raw_import: str,
        line_number: int,
        repo_files_set: Set[str],
    ) -> List[DependencyItem]:
        match = re.search(r"import\s+(?:static\s+)?([A-Za-z0-9_\.]+)\s*;?", raw_import)
        if not match:
            return []

        full_import = match.group(1).strip()
        if full_import.startswith("java.") or full_import.startswith("javax.") or full_import.startswith("org.junit."):
            return [
                DependencyItem(
                    source_file=source_file,
                    target_file=None,
                    raw_import=raw_import,
                    module_name=full_import,
                    imported_symbols=[],
                    dependency_type=DependencyType.EXTERNAL,
                    resolution_status=ResolutionStatus.EXTERNAL,
                    line_number=line_number,
                )
            ]

        # Convert package dots to path
        pkg_path = full_import.replace(".", "/") + ".java"
        for repo_file in repo_files_set:
            if repo_file.endswith(pkg_path):
                return [
                    DependencyItem(
                        source_file=source_file,
                        target_file=repo_file,
                        raw_import=raw_import,
                        module_name=full_import,
                        imported_symbols=[full_import.split(".")[-1]],
                        dependency_type=DependencyType.INTERNAL,
                        resolution_status=ResolutionStatus.RESOLVED,
                        line_number=line_number,
                    )
                ]

        return [
            DependencyItem(
                source_file=source_file,
                target_file=None,
                raw_import=raw_import,
                module_name=full_import,
                imported_symbols=[],
                dependency_type=DependencyType.UNKNOWN,
                resolution_status=ResolutionStatus.UNRESOLVED,
                line_number=line_number,
            )
        ]

    # -------------------------------------------------------------------------
    # 4. GO RESOLVER
    # -------------------------------------------------------------------------
    @classmethod
    def _resolve_go_import(
        cls,
        source_file: str,
        raw_import: str,
        line_number: int,
        repo_files_set: Set[str],
    ) -> List[DependencyItem]:
        match = re.search(r"['\"]([^'\"]+)['\"]", raw_import)
        if not match:
            return []

        import_path = match.group(1).strip()
        if import_path in GO_STDLIB or "/" not in import_path:
            return [
                DependencyItem(
                    source_file=source_file,
                    target_file=None,
                    raw_import=raw_import,
                    module_name=import_path,
                    imported_symbols=[],
                    dependency_type=DependencyType.EXTERNAL,
                    resolution_status=ResolutionStatus.EXTERNAL,
                    line_number=line_number,
                )
            ]

        # Check internal go packages
        parts = import_path.split("/")
        for idx in range(len(parts)):
            sub_path = "/".join(parts[idx:])
            for repo_file in repo_files_set:
                if repo_file.endswith(".go") and (sub_path in repo_file or repo_file.startswith(sub_path)):
                    return [
                        DependencyItem(
                            source_file=source_file,
                            target_file=repo_file,
                            raw_import=raw_import,
                            module_name=import_path,
                            imported_symbols=[],
                            dependency_type=DependencyType.INTERNAL,
                            resolution_status=ResolutionStatus.RESOLVED,
                            line_number=line_number,
                        )
                    ]

        return [
            DependencyItem(
                source_file=source_file,
                target_file=None,
                raw_import=raw_import,
                module_name=import_path,
                imported_symbols=[],
                dependency_type=DependencyType.UNKNOWN,
                resolution_status=ResolutionStatus.UNRESOLVED,
                line_number=line_number,
            )
        ]

    # -------------------------------------------------------------------------
    # 5. DEDUPLICATION & MERGING
    # -------------------------------------------------------------------------
    @classmethod
    def _deduplicate_dependencies(cls, items: List[DependencyItem]) -> List[DependencyItem]:
        dedup_map: Dict[Tuple[str, Optional[str], str, int], DependencyItem] = {}

        for item in items:
            key = (item.source_file, item.target_file, item.module_name, item.line_number)
            if key in dedup_map:
                existing = dedup_map[key]
                merged_syms = sorted(list(set(existing.imported_symbols + item.imported_symbols)))
                dedup_map[key] = DependencyItem(
                    source_file=item.source_file,
                    target_file=item.target_file,
                    raw_import=item.raw_import,
                    module_name=item.module_name,
                    imported_symbols=merged_syms,
                    dependency_type=item.dependency_type,
                    resolution_status=item.resolution_status,
                    line_number=item.line_number,
                )
            else:
                dedup_map[key] = item

        return list(dedup_map.values())

    # -------------------------------------------------------------------------
    # 6. CIRCULAR DEPENDENCY DFS DETECTOR
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_circular_dependencies(cls, adj_graph: Dict[str, Set[str]]) -> List[List[str]]:
        cycles: Set[Tuple[str, ...]] = set()

        def dfs(node: str, path: List[str], visited: Set[str]):
            path.append(node)
            visited.add(node)

            for neighbor in adj_graph.get(node, set()):
                if neighbor in path:
                    # Cycle detected! Extract cycle portion
                    idx = path.index(neighbor)
                    raw_cycle = path[idx:] + [neighbor]

                    # Normalize cycle array so smallest element is first (prevents permutations)
                    nodes = raw_cycle[:-1]
                    min_idx = nodes.index(min(nodes))
                    norm_nodes = nodes[min_idx:] + nodes[:min_idx] + [nodes[min_idx]]
                    cycles.add(tuple(norm_nodes))
                elif neighbor not in visited:
                    dfs(neighbor, path, visited)

            path.pop()
            visited.remove(node)

        all_nodes = sorted(list(adj_graph.keys()))
        for start_node in all_nodes:
            dfs(start_node, [], set())

        sorted_cycles = [list(c) for c in cycles]
        sorted_cycles.sort(key=lambda c: (len(c), c))
        return sorted_cycles

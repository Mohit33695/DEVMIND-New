"""
Repository Documentation Service.

Purpose:
Aggregates deterministic repository intelligence (scanned structure, extracted AST symbols, docstrings,
and dependency relationships) into a unified documentation response without using AI/LLMs.
"""

import os
from typing import Dict, List, Optional, Set

from app.schemas.documentation import (
    ArchitectureDocSummary,
    ModuleDocItem,
    OverviewDocSummary,
    RepositoryDocumentationResponse,
)
from app.schemas.symbols import SymbolItem
from app.services.dependency import CodeDependencyService
from app.services.parser.service import CodeIntelligenceService
from app.services.scanner import RepositoryScanner
from app.services.storage import (
    BinaryFileError,
    FileTooLargeError,
    RepositoryNotFoundError,
    RepositoryStorageService,
)


class RepositoryDocumentationService:
    """Service for generating deterministic codebase documentation."""

    SUPPORTED_README_NAMES = {"readme.md", "readme.rst", "readme.txt"}

    @classmethod
    def generate_documentation(cls, repo_id: str) -> RepositoryDocumentationResponse:
        """
        Aggregates scanned file structure, symbol AST data, docstrings, and import graphs
        to produce a deterministic repository documentation response.

        Args:
            repo_id: Unique repository identifier.

        Returns:
            RepositoryDocumentationResponse: Aggregated repository documentation object.

        Raises:
            RepositoryNotFoundError: If repository directory does not exist.
        """
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        # 1. Reuse Scanner Service
        scan_result = RepositoryScanner.scan_extracted_directory(repo_dir)

        # 2. Reuse Symbol Service
        symbols_res = CodeIntelligenceService.extract_repository_symbols(repo_id)

        # Map file_path -> List[SymbolItem]
        file_symbols_map: Dict[str, List[SymbolItem]] = {}
        for file_sym in symbols_res.file_symbols:
            file_symbols_map[file_sym.file_path] = file_sym.symbols

        # 3. Reuse Dependency Service
        dep_res = CodeDependencyService.analyze_repository_dependencies(repo_id)

        # Map file_path -> imports_count & imported_by_count
        imports_count_map: Dict[str, int] = {}
        imported_by_count_map: Dict[str, int] = {}

        for dep in dep_res.dependencies:
            # Source file imports something
            imports_count_map[dep.source_file] = imports_count_map.get(dep.source_file, 0) + 1

            # Target file is imported by source_file
            if dep.target_file:
                imported_by_count_map[dep.target_file] = (
                    imported_by_count_map.get(dep.target_file, 0) + 1
                )

        # 4. Detect README content deterministically
        readme_file_path: Optional[str] = None
        readme_content: Optional[str] = None

        # Prioritize root level README first, then any scanned README
        sorted_files = sorted(scan_result.scanned_files)
        candidate_readmes: List[str] = []

        for f in sorted_files:
            base_lower = os.path.basename(f).lower()
            if base_lower in cls.SUPPORTED_README_NAMES:
                candidate_readmes.append(f)

        # Sort candidate readmes so root 'README.md' / 'README.txt' comes first
        candidate_readmes.sort(key=lambda path: (path.count("/"), path.lower()))

        if candidate_readmes:
            readme_file_path = candidate_readmes[0]
            try:
                content_res = RepositoryStorageService.read_repository_file_content(
                    repo_id, readme_file_path
                )
                readme_content = content_res.content
            except (BinaryFileError, FileTooLargeError, Exception):
                readme_content = None

        # 5. Build Module Documentation Items
        # Combine scanned files & files with symbols
        all_file_paths: Set[str] = set(scan_result.scanned_files)
        all_file_paths.update(file_symbols_map.keys())

        modules: List[ModuleDocItem] = []
        for file_path in sorted(list(all_file_paths)):
            lang = RepositoryScanner.detect_language(file_path)
            symbols = file_symbols_map.get(file_path, [])
            total_symbols = len(symbols)

            # Calculate public symbols count
            public_count = 0
            summary_docstring: Optional[str] = None

            for sym in symbols:
                # Visibility check
                if sym.visibility == "public":
                    public_count += 1
                elif (sym.visibility is None or sym.visibility == "") and not sym.name.startswith("_"):
                    public_count += 1

                # First non-empty docstring as module summary docstring
                if summary_docstring is None and sym.docstring and sym.docstring.strip():
                    summary_docstring = sym.docstring.strip()

            modules.append(
                ModuleDocItem(
                    file_path=file_path,
                    language=lang,
                    summary_docstring=summary_docstring,
                    total_symbols=total_symbols,
                    public_symbols_count=public_count,
                    symbols=symbols,
                    imports_count=imports_count_map.get(file_path, 0),
                    imported_by_count=imported_by_count_map.get(file_path, 0),
                )
            )

        # Deterministic module sorting
        modules.sort(key=lambda m: m.file_path)

        # 6. Extract External Packages from Dependencies
        external_pkgs_set: Set[str] = set()
        for dep in dep_res.dependencies:
            if dep.dependency_type == "external" and dep.module_name:
                external_pkgs_set.add(dep.module_name)

        # 7. Construct Final Overview & Architecture Summaries
        overview = OverviewDocSummary(
            repo_id=repo_id,
            total_files=scan_result.total_files,
            total_symbols=symbols_res.total_symbols,
            detected_languages=scan_result.detected_languages,
            readme_file_path=readme_file_path,
            readme_content=readme_content,
        )

        architecture = ArchitectureDocSummary(
            total_internal_dependencies=dep_res.internal_dependencies_count,
            external_packages=sorted(list(external_pkgs_set)),
            has_circular_dependencies=dep_res.has_circular_dependencies,
            circular_cycles_count=len(dep_res.circular_dependency_cycles),
        )

        return RepositoryDocumentationResponse(
            repo_id=repo_id,
            overview=overview,
            architecture=architecture,
            modules=modules,
        )

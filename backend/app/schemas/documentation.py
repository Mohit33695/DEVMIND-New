"""
Repository Documentation Schemas.

Purpose:
Defines Pydantic data schemas for automated, deterministic repository documentation response models.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
from app.schemas.symbols import SymbolItem


class ModuleDocItem(BaseModel):
    """Documentation summary for a single codebase module/file."""

    file_path: str
    language: str
    summary_docstring: Optional[str] = None
    total_symbols: int
    public_symbols_count: int
    symbols: List[SymbolItem] = []
    imports_count: int = 0
    imported_by_count: int = 0


class OverviewDocSummary(BaseModel):
    """High-level repository documentation overview."""

    repo_id: str
    total_files: int
    total_symbols: int
    detected_languages: Dict[str, int] = {}
    readme_file_path: Optional[str] = None
    readme_content: Optional[str] = None


class ArchitectureDocSummary(BaseModel):
    """Architectural documentation summary derived from dependencies."""

    total_internal_dependencies: int
    external_packages: List[str] = []
    has_circular_dependencies: bool = False
    circular_cycles_count: int = 0


class RepositoryDocumentationResponse(BaseModel):
    """Complete repository documentation intelligence response."""

    repo_id: str
    overview: OverviewDocSummary
    architecture: ArchitectureDocSummary
    modules: List[ModuleDocItem] = []

"""
Pydantic schemas for repository dependency models.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DependencyType(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    EXTERNAL = "external"
    UNRESOLVED = "unresolved"


class DependencyItem(BaseModel):
    """Represents an individual import dependency relationship."""

    source_file: str = Field(..., description="Relative path of file declaring import")
    target_file: Optional[str] = Field(None, description="Resolved relative path of target repo file (if internal)")
    raw_import: str = Field(..., description="Original import statement text")
    module_name: str = Field(..., description="Extracted module specifier string")
    imported_symbols: List[str] = Field(default_factory=list, description="Names of imported symbols if applicable")
    dependency_type: DependencyType = Field(..., description="internal | external | unknown")
    resolution_status: ResolutionStatus = Field(..., description="resolved | external | unresolved")
    line_number: int = Field(..., description="1-indexed line start number")


class RepositoryDependenciesResponse(BaseModel):
    """API response model for repository dependency analysis."""

    repo_id: str = Field(..., description="Repository unique identifier")
    total_files: int = Field(..., description="Total count of non-ignored files in repository")
    total_dependencies: int = Field(..., description="Total count of import dependencies analyzed")
    internal_dependencies_count: int = Field(..., description="Count of resolved internal dependencies")
    external_dependencies_count: int = Field(..., description="Count of external library dependencies")
    unresolved_dependencies_count: int = Field(..., description="Count of unresolved or unknown dependencies")
    has_circular_dependencies: bool = Field(..., description="True if circular import cycles exist")
    circular_dependency_cycles: List[List[str]] = Field(
        default_factory=list, description="List of circular path cycles"
    )
    dependencies: List[DependencyItem] = Field(
        default_factory=list, description="Extracted dependency list"
    )

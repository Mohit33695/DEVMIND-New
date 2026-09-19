"""
Code Quality Schemas.

Purpose:
Defines Pydantic data schemas for deterministic codebase quality analysis.
"""

from typing import List, Optional
from pydantic import BaseModel


class QualityFindingItem(BaseModel):
    """Specific quality finding evaluated against deterministic rules."""

    id: str
    file_path: str
    rule_id: str  # LONG_FUNCTION, EXCESSIVE_PARAMETERS, LARGE_CLASS, VERY_LONG_FILE, MISSING_DOCSTRING, CIRCULAR_DEPENDENCY, UNRESOLVED_IMPORT
    rule_name: str
    category: str  # complexity, maintainability, documentation, architecture
    severity: str  # HIGH, MEDIUM, LOW
    finding_type: str = "HEURISTIC_RISK"  # VERIFIED_FACT or HEURISTIC_RISK
    message: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    symbol_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None


class QualityMetricsSummary(BaseModel):
    """High-level aggregated codebase maintainability & quality summary."""

    total_findings: int
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    documentation_coverage_percentage: float
    average_function_length: float
    average_parameters_per_function: float
    large_files_count: int
    long_functions_count: int


class FileQualitySummary(BaseModel):
    """Quality & complexity health overview per codebase file."""

    file_path: str
    language: str
    total_lines: int
    total_symbols: int
    findings_count: int


class RepositoryQualityResponse(BaseModel):
    """Complete Code Quality Intelligence response."""

    repo_id: str
    summary: QualityMetricsSummary
    findings: List[QualityFindingItem] = []
    files_summary: List[FileQualitySummary] = []

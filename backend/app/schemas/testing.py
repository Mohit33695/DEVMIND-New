"""
Testing Intelligence Schemas.

Purpose:
Defines Pydantic data schemas for static testing analysis, test suite inventory,
framework detection, assertion counts, and source-to-test mapping heuristics.
"""

from typing import List, Optional
from pydantic import BaseModel


class TestFileSummary(BaseModel):
    """Summary of an identified test suite file."""

    file_path: str
    language: str
    framework: str
    test_function_count: int
    assertion_count: int


class SourceTestMapping(BaseModel):
    """Heuristic mapping from a source code file to its matching test file."""

    source_file: str
    has_obvious_test: bool
    matching_test_file: Optional[str] = None
    confidence: str  # "HIGH", "MEDIUM", "LOW", "NONE"


class TestingFindingItem(BaseModel):
    """Specific static testing signal or quality finding."""

    id: str
    file_path: str
    rule_id: str  # TEST_FILE_DETECTED, TEST_FRAMEWORK_DETECTED, TEST_SUITE_WITHOUT_ASSERTIONS, SOURCE_FILE_WITHOUT_OBVIOUS_TEST, PUBLIC_FUNCTION_WITHOUT_OBVIOUS_TEST
    rule_name: str
    category: str  # inventory, framework, quality, coverage_gap
    classification: str  # VERIFIED_STATIC_FACT or HEURISTIC_TESTING_SIGNAL
    severity: str  # INFO, LOW, MEDIUM, HIGH
    message: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    evidence: str
    remediation: str


class TestingMetricsSummary(BaseModel):
    """High-level aggregated static testing metrics."""

    total_test_files: int
    total_test_functions: int
    total_assertions_detected: int
    total_source_files: int
    source_files_with_tests: int
    source_files_without_tests: int
    estimated_test_ratio: float  # Static ratio: (source_files_with_tests / total_source_files) * 100
    detected_frameworks: List[str]
    test_directories: List[str]


class RepositoryTestingResponse(BaseModel):
    """Complete Testing Intelligence API response."""

    repo_id: str
    metrics: TestingMetricsSummary
    test_files: List[TestFileSummary] = []
    source_mappings: List[SourceTestMapping] = []
    findings: List[TestingFindingItem] = []

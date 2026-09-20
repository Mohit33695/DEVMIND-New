"""
Security Intelligence Schemas.

Purpose:
Defines Pydantic data schemas for static application security testing (SAST)
and credentials / vulnerability findings.
"""

from typing import List, Optional
from pydantic import BaseModel


class SecurityFindingItem(BaseModel):
    """Specific security finding evaluated against static rules."""

    id: str
    file_path: str
    rule_id: str
    rule_name: str
    category: str  # secrets, code_execution, crypto, web_security, configuration
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    classification: str  # VERIFIED_STATIC_FINDING or HEURISTIC_SECURITY_RISK
    message: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    evidence: str
    remediation: str


class SecurityMetricsSummary(BaseModel):
    """High-level aggregated security risk summary."""

    total_findings: int
    critical_severity_count: int
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    secrets_count: int
    code_execution_count: int
    web_security_count: int


class RepositorySecurityResponse(BaseModel):
    """Complete Security Intelligence response."""

    repo_id: str
    summary: SecurityMetricsSummary
    findings: List[SecurityFindingItem] = []

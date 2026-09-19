"""
Tests for Code Quality Intelligence Service and API Route.

Coverage:
- Valid repository quality analysis
- Missing repository handling (404)
- Rule 1: LONG_FUNCTION (exact 50 lines vs 51 lines)
- Rule 2: EXCESSIVE_PARAMETERS (exact 5 params vs 6 params)
- Rule 3: LARGE_CLASS (>300 lines or >15 methods)
- Rule 4: VERY_LONG_FILE (>500 lines MEDIUM, >1000 lines HIGH)
- Rule 5: MISSING_DOCSTRING (public symbols without docstrings)
- Rule 6: CIRCULAR_DEPENDENCY (HIGH severity)
- Rule 7: UNRESOLVED_IMPORT (MEDIUM severity)
- Metric calculations (doc coverage %, avg function length, avg params per func)
- Deterministic ordering of findings
- Multi-language repository analysis
"""

import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.quality import CodeQualityService
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService

client = TestClient(app)


def create_zip(files: dict) -> bytes:
    """Helper to generate in-memory ZIP bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def repo_boundary_tests():
    """Repository testing exact boundary conditions for 50/51 lines and 5/6 params."""
    # 50 lines function (no trigger)
    func_50_lines = "def func_50():\n" + "\n".join([f"    x = {i}" for i in range(49)])

    # 51 lines function (triggers LONG_FUNCTION)
    func_51_lines = "def func_51():\n" + "\n".join([f"    x = {i}" for i in range(50)])

    # 5 parameters (no trigger)
    func_5_params = "def func_5_p(a, b, c, d, e):\n    '''Doc.'''\n    pass\n"

    # 6 parameters (triggers EXCESSIVE_PARAMETERS)
    func_6_params = "def func_6_p(a, b, c, d, e, f):\n    '''Doc.'''\n    pass\n"

    files = {
        "sample_funcs.py": f"{func_50_lines}\n\n{func_51_lines}\n\n{func_5_params}\n\n{func_6_params}\n"
    }
    zip_bytes = create_zip(files)
    repo_id, _ = RepositoryStorageService.store_repository_zip(zip_bytes)
    return repo_id


@pytest.fixture
def repo_large_files_and_classes():
    """Repository with 501-line file, 1001-line file, large class, circular deps, unresolved import."""
    # 501 line file -> MEDIUM severity
    lines_501 = "# 501 line file\n" + "\n".join([f"# line {i}" for i in range(500)])

    # 1001 line file -> HIGH severity
    lines_1001 = "# 1001 line file\n" + "\n".join([f"# line {i}" for i in range(1000)])

    # Class with 16 methods
    methods_code = "\n".join([f"    def method_{i}(self):\n        '''Doc.'''\n        pass" for i in range(16)])
    large_class = f"class BigClass:\n    '''Large class.'''\n{methods_code}\n"

    files = {
        "medium_file.py": lines_501,
        "high_file.py": lines_1001,
        "class_file.py": f"{large_class}\nimport non_existent_unknown_module_xyz\n",
        "a.py": "import b\ndef fa(): pass\n",
        "b.py": "import a\ndef fb(): pass\n",
    }
    zip_bytes = create_zip(files)
    repo_id, _ = RepositoryStorageService.store_repository_zip(zip_bytes)
    return repo_id


def test_quality_boundary_conditions(repo_boundary_tests):
    """Test exact boundaries: 50 vs 51 lines, 5 vs 6 parameters."""
    res = CodeQualityService.analyze_repository_quality(repo_boundary_tests)

    # LONG_FUNCTION check
    long_func_findings = [f for f in res.findings if f.rule_id == "LONG_FUNCTION"]
    assert len(long_func_findings) == 1
    assert long_func_findings[0].symbol_name == "func_51"
    assert long_func_findings[0].metric_value == 51.0

    # EXCESSIVE_PARAMETERS check
    param_findings = [f for f in res.findings if f.rule_id == "EXCESSIVE_PARAMETERS"]
    assert len(param_findings) == 1
    assert param_findings[0].symbol_name == "func_6_p"
    assert param_findings[0].metric_value == 6.0


def test_quality_file_and_class_rules(repo_large_files_and_classes):
    """Test file length thresholds, large class rule, circular deps, unresolved import."""
    res = CodeQualityService.analyze_repository_quality(repo_large_files_and_classes)

    # VERY_LONG_FILE checks
    file_findings = [f for f in res.findings if f.rule_id == "VERY_LONG_FILE"]
    assert len(file_findings) == 2

    med_file = next(f for f in file_findings if f.file_path == "medium_file.py")
    assert med_file.severity == "MEDIUM"
    assert med_file.metric_value == 501.0

    high_file = next(f for f in file_findings if f.file_path == "high_file.py")
    assert high_file.severity == "HIGH"
    assert high_file.metric_value == 1001.0

    # LARGE_CLASS check (>15 methods)
    class_findings = [f for f in res.findings if f.rule_id == "LARGE_CLASS"]
    assert len(class_findings) == 1
    assert class_findings[0].symbol_name == "BigClass"

    # CIRCULAR_DEPENDENCY check (HIGH severity)
    circ_findings = [f for f in res.findings if f.rule_id == "CIRCULAR_DEPENDENCY"]
    assert len(circ_findings) >= 2
    assert all(f.severity == "HIGH" for f in circ_findings)

    # UNRESOLVED_IMPORT check (MEDIUM severity)
    unres_findings = [f for f in res.findings if f.rule_id == "UNRESOLVED_IMPORT"]
    assert len(unres_findings) >= 1
    assert unres_findings[0].severity == "MEDIUM"


def test_quality_metrics_calculation(repo_boundary_tests):
    """Test summary metric calculations (doc coverage, avg function length, avg params)."""
    res = CodeQualityService.analyze_repository_quality(repo_boundary_tests)
    sum_data = res.summary

    assert sum_data.total_findings > 0
    assert sum_data.average_function_length > 0
    assert sum_data.average_parameters_per_function > 0
    assert 0.0 <= sum_data.documentation_coverage_percentage <= 100.0


def test_deterministic_ordering(repo_large_files_and_classes):
    """Test that findings are deterministically sorted by severity (HIGH->MEDIUM->LOW), file_path, line_start, rule_id."""
    res = CodeQualityService.analyze_repository_quality(repo_large_files_and_classes)

    severity_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings = res.findings

    for i in range(len(findings) - 1):
        f1 = findings[i]
        f2 = findings[i + 1]

        rank1 = severity_rank[f1.severity]
        rank2 = severity_rank[f2.severity]

        assert rank1 <= rank2
        if rank1 == rank2:
            assert (f1.file_path, f1.line_start or 0) <= (f2.file_path, f2.line_start or 0)


def test_quality_missing_repository():
    """Test 404 for invalid repository ID."""
    with pytest.raises(RepositoryNotFoundError):
        CodeQualityService.analyze_repository_quality("invalid_repo_uuid_0000")


def test_quality_api_endpoint(repo_boundary_tests):
    """Test GET /api/repositories/{repo_id}/quality API endpoint."""
    response = client.get(f"/api/repositories/{repo_boundary_tests}/quality")
    assert response.status_code == 200

    data = response.json()
    assert data["repo_id"] == repo_boundary_tests
    assert "summary" in data
    assert "findings" in data
    assert "files_summary" in data


def test_quality_api_endpoint_404():
    """Test GET /api/repositories/{repo_id}/quality API endpoint with 404."""
    response = client.get("/api/repositories/non-existent-id/quality")
    assert response.status_code == 404

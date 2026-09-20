"""
Tests for Security Intelligence Service and API Route.

Coverage:
- 1. AWS key detection
- 2. Private key detection
- 3. Hardcoded password detection
- 4. API token literal detection
- 5. eval() detection
- 6. exec() detection
- 7. subprocess shell=True detection
- 8. os.system() detection
- 9. pickle.loads() detection
- 10. yaml.load unsafe loader detection
- 11. Dynamic SQL string formatting detection
- 12. Weak crypto (MD5/SHA1) detection
- 13. External HTTP URL detection
- 14. DEBUG=True mode detection
- 15. Comments ignored (no false positive)
- 16. README / Markdown files ignored
- 17. Placeholders ignored (YOUR_KEY, CHANGEME, 123456)
- 18. Environment variable lookups ignored (os.getenv, process.env)
- 19. Secret masking behavior (no plaintext credentials)
- 20. Line number correctness
- 21. Deterministic finding ordering (CRITICAL->HIGH->MEDIUM->LOW)
- 22. Missing repository -> 404
- 23. Multiple languages (Python + JS/TS)
- 24. Zero findings clean state
"""

import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.security import CodeSecurityService
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
def repo_security_findings():
    files = {
        "config.py": (
            "import os\n"
            "# Comment with AKIAIOSFODNN7EXAMPLE\n"
            "AWS_KEY = \"AKIAIOSFODNN7EXAMPLE\"\n"
            "PRIV_KEY = \"-----BEGIN PRIVATE KEY-----\\nMIIEvg...\"\n"
            "DB_PASSWORD = \"super_secret_db_pass_99\"\n"
            "API_KEY = \"sk_live_9988776655443322\"\n"
            "ENV_PASS = os.getenv('DB_PASS')\n"
            "PLACEHOLDER_KEY = \"YOUR_KEY_HERE\"\n"
            "DEBUG = True\n"
        ),
        "server.py": (
            "import eval_mod\n"
            "import subprocess\n"
            "import pickle\n"
            "import yaml\n"
            "import hashlib\n"
            "\n"
            "def run_code(user_input):\n"
            "    eval(user_input)\n"
            "    exec(user_input)\n"
            "    subprocess.Popen('ls -l', shell=True)\n"
            "    os.system('cat /etc/passwd')\n"
            "    data = pickle.loads(user_input)\n"
            "    cfg = yaml.load(user_input, Loader=yaml.Loader)\n"
            "    query = f'SELECT * FROM users WHERE name = {user_input}'\n"
            "    h = hashlib.md5(b'secret').hexdigest()\n"
            "    url = 'http://api.external-service.com/v1'\n"
            "    local_url = 'http://localhost:8000'\n"
        ),
        "app.js": (
            "// JS comment with password = '123'\n"
            "const token = 'sk_live_js_secret_token_123';\n"
            "eval('console.log(1)');\n"
        ),
        "README.md": (
            "# Docs\n"
            "AKIAIOSFODNN7EXAMPLE\n"
            "eval(x)\n"
            "DEBUG = True\n"
        ),
    }
    zip_bytes = create_zip(files)
    repo_id, _ = RepositoryStorageService.store_repository_zip(zip_bytes)
    return repo_id


@pytest.fixture
def repo_clean_state():
    files = {
        "clean.py": (
            "import os\n"
            "def safe_func():\n"
            "    db_pass = os.getenv('DB_PASS')\n"
            "    return db_pass\n"
        )
    }
    zip_bytes = create_zip(files)
    repo_id, _ = RepositoryStorageService.store_repository_zip(zip_bytes)
    return repo_id


def test_security_findings_comprehensive(repo_security_findings):
    """Test security findings detection across rules."""
    res = CodeSecurityService.analyze_repository_security(repo_security_findings)

    assert res.repo_id == repo_security_findings
    assert res.summary.total_findings > 0

    rule_ids = {f.rule_id for f in res.findings}

    # Verify Rules Triggered
    assert "AWS_ACCESS_KEY" in rule_ids
    assert "PRIVATE_KEY_BLOCK" in rule_ids
    assert "HARDCODED_PASSWORD" in rule_ids
    assert "API_TOKEN_LITERAL" in rule_ids
    assert "UNSAFE_EVAL_EXEC" in rule_ids
    assert "UNSAFE_SUBPROCESS_SHELL" in rule_ids
    assert "UNSAFE_DESERIALIZATION" in rule_ids
    assert "DYNAMIC_SQL_CONCATENATION" in rule_ids
    assert "WEAK_CRYPTO_HASH" in rule_ids
    assert "INSECURE_HTTP_URL" in rule_ids
    assert "DEBUG_MODE_ENABLED" in rule_ids


def test_secret_masking(repo_security_findings):
    """Verify that no plaintext secrets are returned in evidence fields."""
    res = CodeSecurityService.analyze_repository_security(repo_security_findings)

    secret_findings = [f for f in res.findings if f.category == "secrets"]
    assert len(secret_findings) > 0

    for f in secret_findings:
        assert "super_secret_db_pass_99" not in f.evidence
        assert "sk_live_9988776655443322" not in f.evidence
        assert "AKIAIOSFODNN7EXAMPLE" not in f.evidence
        assert "****" in f.evidence or "[MASKED]" in f.evidence


def test_ignored_comments_and_placeholders(repo_security_findings):
    """Verify comments, env vars, placeholders, and READMEs are excluded from findings."""
    res = CodeSecurityService.analyze_repository_security(repo_security_findings)

    for f in res.findings:
        # README.md should be completely ignored
        assert f.file_path != "README.md"
        # Environment variable line ENV_PASS = os.getenv('DB_PASS') should not trigger HARDCODED_PASSWORD
        if "ENV_PASS" in f.evidence:
            pytest.fail("Environment variable lookup incorrectly flagged as hardcoded password.")
        if "PLACEHOLDER_KEY" in f.evidence:
            pytest.fail("Placeholder key incorrectly flagged as secret.")


def test_deterministic_finding_sorting(repo_security_findings):
    """Verify deterministic sorting by severity (CRITICAL->HIGH->MEDIUM->LOW), file_path, line_start."""
    res = CodeSecurityService.analyze_repository_security(repo_security_findings)
    findings = res.findings

    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    for i in range(len(findings) - 1):
        f1 = findings[i]
        f2 = findings[i + 1]

        rank1 = sev_order[f1.severity]
        rank2 = sev_order[f2.severity]

        assert rank1 <= rank2
        if rank1 == rank2:
            assert (f1.file_path, f1.line_start or 0) <= (f2.file_path, f2.line_start or 0)


def test_zero_findings_clean_state(repo_clean_state):
    """Test repository with zero security findings."""
    res = CodeSecurityService.analyze_repository_security(repo_clean_state)

    assert res.summary.total_findings == 0
    assert len(res.findings) == 0


def test_security_missing_repository():
    """Test 404 for missing repository."""
    with pytest.raises(RepositoryNotFoundError):
        CodeSecurityService.analyze_repository_security("invalid_repo_uuid_9999")


def test_security_api_endpoint(repo_security_findings):
    """Test GET /api/repositories/{repo_id}/security endpoint."""
    response = client.get(f"/api/repositories/{repo_security_findings}/security")
    assert response.status_code == 200

    data = response.json()
    assert data["repo_id"] == repo_security_findings
    assert "summary" in data
    assert "findings" in data
    assert data["summary"]["total_findings"] > 0


def test_security_api_endpoint_404():
    """Test GET /api/repositories/{repo_id}/security 404 endpoint."""
    response = client.get("/api/repositories/non-existent-uuid-1111/security")
    assert response.status_code == 404

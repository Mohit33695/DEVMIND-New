"""
Security Intelligence Service.

Purpose:
Statically audits repository files for hardcoded secrets, dangerous code execution,
weak cryptography, insecure URLs, and unsafe configurations without running code or external APIs.
"""

import os
import re
from typing import Dict, List, Set, Tuple

from app.schemas.security import (
    RepositorySecurityResponse,
    SecurityFindingItem,
    SecurityMetricsSummary,
)
from app.services.scanner import RepositoryScanner
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService


class CodeSecurityService:
    """Service for static application security auditing."""

    SEVERITY_ORDER: Dict[str, int] = {
        "CRITICAL": 0,
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3,
    }

    DOC_EXTENSIONS: Set[str] = {
        ".md",
        ".rst",
        ".txt",
        ".markdown",
        ".json",
        ".svg",
        ".html",
    }

    PLACEHOLDER_WORDS: Set[str] = {
        "your_key",
        "your_api_key",
        "your_password",
        "changeme",
        "example",
        "placeholder",
        "123456",
        "xxxx",
        "test",
        "dummy",
    }

    @classmethod
    def _is_placeholder(cls, line: str, val: str = "") -> bool:
        """Helper to identify environment variables or obvious dummy placeholder values."""
        line_l = line.lower()
        if "os.getenv" in line_l or "os.environ" in line_l or "process.env" in line_l:
            return True
        val_l = val.lower().strip()
        if val_l in cls.PLACEHOLDER_WORDS:
            return True
        if val_l.startswith("your_") or val_l.endswith("_here"):
            return True
        return False

    @classmethod
    def _mask_secret(cls, secret: str) -> str:
        """Masks sensitive secret strings so plaintext credentials are never returned."""
        if not secret:
            return "****"
        secret_str = str(secret).strip()
        if len(secret_str) <= 6:
            return "****"
        prefix = secret_str[:4]
        return f"{prefix}...****"

    @classmethod
    def _is_comment_line(cls, line: str) -> bool:
        """Determines if a code line is a comment."""
        stripped = line.strip()
        return (
            stripped.startswith("#")
            or stripped.startswith("//")
            or stripped.startswith("/*")
            or stripped.startswith("*")
            or stripped.startswith("<!--")
        )

    @classmethod
    def analyze_repository_security(cls, repo_id: str) -> RepositorySecurityResponse:
        """
        Statically evaluates security risk rules across stored repository files.

        Args:
            repo_id: Unique repository identifier.

        Returns:
            RepositorySecurityResponse: Aggregated security findings and metrics summary.

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

        findings: List[SecurityFindingItem] = []
        finding_id_counter = 1

        # Compiled RegEx Rules
        re_aws_key = re.compile(r"AKIA[0-9A-Z]{16}")
        re_priv_key = re.compile(r"-----BEGIN (?:RSA |EC |PGP |DSA )?PRIVATE KEY-----")
        re_password = re.compile(
            r"(?i)(?:password|db_password|secret_pass)\s*[:=]\s*[\"']([^\"']{4,})[\"']"
        )
        re_api_token = re.compile(
            r"(?i)(?:api_key|secret_token|auth_token|access_token)\s*[:=]\s*[\"']([^\"']{8,})[\"']"
        )
        re_eval_exec = re.compile(r"\b(eval|exec)\s*\(")
        re_subprocess = re.compile(
            r"subprocess\.(?:Popen|run|call|check_output)\s*\([^)]*shell\s*=\s*True|os\.system\s*\("
        )
        re_pickle_yaml = re.compile(
            r"pickle\.loads?\s*\(|yaml\.load\s*\([^)]*Loader\s*=\s*yaml\.(?:Loader|UnsafeLoader)"
        )
        re_sql_concat = re.compile(
            r"(?i)(?:f[\"'][^\"']*(?:select|insert|update|delete)|(?:\bselect|\binsert|\bupdate|\bdelete)\s+[^\"']*(?:\.format\(|\+|\%))"
        )
        re_weak_crypto = re.compile(r"(?i)\b(md5|sha1)\b")
        re_http_url = re.compile(
            r"http://(?!(?:localhost|127\.0\.0\.1|schema\.org|w3\.org))[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        )
        re_debug_true = re.compile(r"(?i)\bDEBUG\s*=\s*True\b|\bapp\.debug\s*=\s*True\b")

        # 2. Iterate through scanned files safely
        for rel_file_path in scan_result.scanned_files:
            base_name = os.path.basename(rel_file_path).lower()
            _, ext = os.path.splitext(rel_file_path.lower())

            # Rule Exclusion: Documentation files, READMEs, licenses
            if (
                ext in cls.DOC_EXTENSIONS
                or "readme" in base_name
                or "license" in base_name
                or "changelog" in base_name
            ):
                continue

            abs_path = os.path.join(repo_dir, rel_file_path)

            # Skip size cap > 2 MB or binary files
            try:
                if os.path.getsize(abs_path) > RepositoryStorageService.MAX_FILE_READ_SIZE_BYTES:
                    continue
                with open(abs_path, "rb") as f:
                    raw_bytes = f.read()
                if b"\x00" in raw_bytes[:1024]:
                    continue
                file_text = raw_bytes.decode("utf-8", errors="ignore")
            except Exception:
                continue

            lines = file_text.splitlines()

            for line_idx, line in enumerate(lines, start=1):
                # Rule Exclusion: Ignore comments
                if cls._is_comment_line(line):
                    continue

                line_lower = line.lower()

                # RULE 1: AWS_ACCESS_KEY
                aws_match = re_aws_key.search(line)
                if aws_match and not cls._is_placeholder(line):
                    matched_key = aws_match.group(0)
                    masked = cls._mask_secret(matched_key)
                    findings.append(
                        SecurityFindingItem(
                            id=f"sec-{finding_id_counter}",
                            file_path=rel_file_path,
                            rule_id="AWS_ACCESS_KEY",
                            rule_name="Hardcoded AWS Access Key",
                            category="secrets",
                            severity="CRITICAL",
                            classification="VERIFIED_STATIC_FINDING",
                            message="AWS access-key-like credential detected.",
                            line_start=line_idx,
                            line_end=line_idx,
                            evidence=f"Matched pattern: {masked}",
                            remediation="Rotate the AWS access key immediately and store credentials in environment variables or a secret management service.",
                        )
                    )
                    finding_id_counter += 1

                # RULE 2: PRIVATE_KEY_BLOCK
                if re_priv_key.search(line):
                    findings.append(
                        SecurityFindingItem(
                            id=f"sec-{finding_id_counter}",
                            file_path=rel_file_path,
                            rule_id="PRIVATE_KEY_BLOCK",
                            rule_name="Private Key Header Block",
                            category="secrets",
                            severity="CRITICAL",
                            classification="VERIFIED_STATIC_FINDING",
                            message="PEM private key block header detected in source file.",
                            line_start=line_idx,
                            line_end=line_idx,
                            evidence="-----BEGIN PRIVATE KEY----- [MASKED]",
                            remediation="Remove private key files from the codebase and use a secure key vault or secret manager.",
                        )
                    )
                    finding_id_counter += 1

                # RULE 3: HARDCODED_PASSWORD
                pw_match = re_password.search(line)
                if pw_match and not cls._is_placeholder(line):
                    val = pw_match.group(1)
                    if val and not cls._is_placeholder(line, val):
                        masked_val = cls._mask_secret(val)
                        findings.append(
                            SecurityFindingItem(
                                id=f"sec-{finding_id_counter}",
                                file_path=rel_file_path,
                                rule_id="HARDCODED_PASSWORD",
                                rule_name="Hardcoded Password",
                                category="secrets",
                                severity="CRITICAL",
                                classification="VERIFIED_STATIC_FINDING",
                                message="Hardcoded password assignment detected.",
                                line_start=line_idx,
                                line_end=line_idx,
                                evidence=f"Password assignment value: '{masked_val}'",
                                remediation="Store sensitive database passwords and credentials in environment variables or configuration vaults.",
                            )
                        )
                        finding_id_counter += 1

                # RULE 4: API_TOKEN_LITERAL
                tok_match = re_api_token.search(line)
                if tok_match and not cls._is_placeholder(line):
                    val = tok_match.group(1)
                    if val and not cls._is_placeholder(line, val):
                        masked_val = cls._mask_secret(val)
                        findings.append(
                            SecurityFindingItem(
                                id=f"sec-{finding_id_counter}",
                                file_path=rel_file_path,
                                rule_id="API_TOKEN_LITERAL",
                                rule_name="Hardcoded API Token / Secret",
                                category="secrets",
                                severity="CRITICAL",
                                classification="VERIFIED_STATIC_FINDING",
                                message="Hardcoded API token or secret assignment detected.",
                                line_start=line_idx,
                                line_end=line_idx,
                                evidence=f"Token assignment value: '{masked_val}'",
                                remediation="Extract API keys and tokens into environment variables or secure key vaults.",
                            )
                        )
                        finding_id_counter += 1

                # RULE 5: UNSAFE_EVAL_EXEC
                if re_eval_exec.search(line):
                    findings.append(
                        SecurityFindingItem(
                            id=f"sec-{finding_id_counter}",
                            file_path=rel_file_path,
                            rule_id="UNSAFE_EVAL_EXEC",
                            rule_name="Dynamic Code Evaluation (eval/exec)",
                            category="code_execution",
                            severity="HIGH",
                            classification="HEURISTIC_SECURITY_RISK",
                            message="Dynamic code evaluation function (eval/exec) detected.",
                            line_start=line_idx,
                            line_end=line_idx,
                            evidence=line.strip()[:100],
                            remediation="Avoid dynamic code execution with eval() or exec(). Use safe parsing or explicit control flows instead.",
                        )
                    )
                    finding_id_counter += 1

                # RULE 6: UNSAFE_SUBPROCESS_SHELL
                if re_subprocess.search(line):
                    findings.append(
                        SecurityFindingItem(
                            id=f"sec-{finding_id_counter}",
                            file_path=rel_file_path,
                            rule_id="UNSAFE_SUBPROCESS_SHELL",
                            rule_name="Subprocess Shell Execution",
                            category="code_execution",
                            severity="HIGH",
                            classification="HEURISTIC_SECURITY_RISK",
                            message="Subprocess invocation with shell=True or os.system() detected.",
                            line_start=line_idx,
                            line_end=line_idx,
                            evidence=line.strip()[:100],
                            remediation="Avoid shell=True in subprocess calls and pass argument lists instead of raw shell command strings to prevent command injection.",
                        )
                    )
                    finding_id_counter += 1

                # RULE 7: UNSAFE_DESERIALIZATION
                if re_pickle_yaml.search(line):
                    findings.append(
                        SecurityFindingItem(
                            id=f"sec-{finding_id_counter}",
                            file_path=rel_file_path,
                            rule_id="UNSAFE_DESERIALIZATION",
                            rule_name="Unsafe Object Deserialization",
                            category="code_execution",
                            severity="HIGH",
                            classification="HEURISTIC_SECURITY_RISK",
                            message="Potentially unsafe object deserialization (pickle/yaml.load) detected.",
                            line_start=line_idx,
                            line_end=line_idx,
                            evidence=line.strip()[:100],
                            remediation="Use safe deserialization practices such as yaml.safe_load() or JSON for untrusted input data.",
                        )
                    )
                    finding_id_counter += 1

                # RULE 8: DYNAMIC_SQL_CONCATENATION
                if re_sql_concat.search(line):
                    findings.append(
                        SecurityFindingItem(
                            id=f"sec-{finding_id_counter}",
                            file_path=rel_file_path,
                            rule_id="DYNAMIC_SQL_CONCATENATION",
                            rule_name="Dynamic SQL Query Construction",
                            category="web_security",
                            severity="MEDIUM",
                            classification="HEURISTIC_SECURITY_RISK",
                            message="Dynamic string formatting or concatenation detected in SQL query statement.",
                            line_start=line_idx,
                            line_end=line_idx,
                            evidence=line.strip()[:100],
                            remediation="Use parameterized SQL queries or ORM query builders to prevent SQL injection risks.",
                        )
                    )
                    finding_id_counter += 1

                # RULE 9: WEAK_CRYPTO_HASH
                if re_weak_crypto.search(line) and any(
                    k in line_lower for k in ["hash", "crypto", "digest", "md5", "sha1"]
                ):
                    findings.append(
                        SecurityFindingItem(
                            id=f"sec-{finding_id_counter}",
                            file_path=rel_file_path,
                            rule_id="WEAK_CRYPTO_HASH",
                            rule_name="Weak Hashing Algorithm (MD5/SHA1)",
                            category="crypto",
                            severity="MEDIUM",
                            classification="HEURISTIC_SECURITY_RISK",
                            message="Weak cryptographic hashing algorithm (MD5/SHA1) detected.",
                            line_start=line_idx,
                            line_end=line_idx,
                            evidence=line.strip()[:100],
                            remediation="Use modern secure hashing algorithms like SHA-256, SHA-512, or bcrypt/argon2 for passwords.",
                        )
                    )
                    finding_id_counter += 1

                # RULE 10: INSECURE_HTTP_URL
                if re_http_url.search(line) and not cls._is_placeholder(line):
                    findings.append(
                        SecurityFindingItem(
                            id=f"sec-{finding_id_counter}",
                            file_path=rel_file_path,
                            rule_id="INSECURE_HTTP_URL",
                            rule_name="Insecure HTTP Protocol Endpoint",
                            category="web_security",
                            severity="LOW",
                            classification="HEURISTIC_SECURITY_RISK",
                            message="Hardcoded unencrypted HTTP URL detected.",
                            line_start=line_idx,
                            line_end=line_idx,
                            evidence=line.strip()[:100],
                            remediation="Use HTTPS URLs for external API calls and service endpoints to protect data in transit.",
                        )
                    )
                    finding_id_counter += 1

                # RULE 11: DEBUG_MODE_ENABLED
                if re_debug_true.search(line) and not cls._is_placeholder(line):
                    findings.append(
                        SecurityFindingItem(
                            id=f"sec-{finding_id_counter}",
                            file_path=rel_file_path,
                            rule_id="DEBUG_MODE_ENABLED",
                            rule_name="Debug Mode Enabled in Code",
                            category="configuration",
                            severity="LOW",
                            classification="VERIFIED_STATIC_FINDING",
                            message="Debug mode configuration set to True.",
                            line_start=line_idx,
                            line_end=line_idx,
                            evidence=line.strip()[:100],
                            remediation="Ensure DEBUG mode is set to False in production environments to avoid leaking diagnostic information.",
                        )
                    )
                    finding_id_counter += 1

        # 3. Deterministic Findings Sorting: CRITICAL -> HIGH -> MEDIUM -> LOW, file_path, line_start, rule_id
        findings.sort(
            key=lambda f: (
                cls.SEVERITY_ORDER.get(f.severity, 99),
                f.file_path,
                f.line_start or 0,
                f.rule_id,
            )
        )

        # 4. Summary Metrics
        crit_cnt = sum(1 for f in findings if f.severity == "CRITICAL")
        high_cnt = sum(1 for f in findings if f.severity == "HIGH")
        med_cnt = sum(1 for f in findings if f.severity == "MEDIUM")
        low_cnt = sum(1 for f in findings if f.severity == "LOW")

        secrets_cnt = sum(1 for f in findings if f.category == "secrets")
        exec_cnt = sum(1 for f in findings if f.category == "code_execution")
        web_cnt = sum(1 for f in findings if f.category == "web_security")

        summary = SecurityMetricsSummary(
            total_findings=len(findings),
            critical_severity_count=crit_cnt,
            high_severity_count=high_cnt,
            medium_severity_count=med_cnt,
            low_severity_count=low_cnt,
            secrets_count=secrets_cnt,
            code_execution_count=exec_cnt,
            web_security_count=web_cnt,
        )

        return RepositorySecurityResponse(
            repo_id=repo_id,
            summary=summary,
            findings=findings,
        )

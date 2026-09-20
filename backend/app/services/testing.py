"""
Testing Intelligence Service.

Purpose:
Statically analyzes repository files for test suites, framework imports, test functions,
assertion counts, and source-to-test mapping heuristics without running code or external APIs.
"""

import os
import re
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.testing import (
    RepositoryTestingResponse,
    SourceTestMapping,
    TestFileSummary,
    TestingFindingItem,
    TestingMetricsSummary,
)
from app.services.parser.service import CodeIntelligenceService
from app.services.scanner import RepositoryScanner
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService


class CodeTestingService:
    """Service for static repository test analysis."""

    DOC_EXTENSIONS: Set[str] = {
        ".md",
        ".rst",
        ".txt",
        ".markdown",
        ".json",
        ".svg",
        ".html",
        ".png",
        ".jpg",
    }

    SEVERITY_ORDER: Dict[str, int] = {
        "CRITICAL": 0,
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3,
        "INFO": 4,
    }

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
    def _is_test_file(cls, rel_path: str) -> bool:
        """Determines whether a file path conforms to static test file conventions."""
        rel_lower = rel_path.lower().replace("\\", "/")
        base_name = os.path.basename(rel_lower)
        _, ext = os.path.splitext(rel_lower)

        # 1. Python
        if ext == ".py":
            if base_name.startswith("test_") or base_name.endswith("_test.py"):
                return True
            parts = rel_lower.split("/")
            if any(p in {"tests", "test", "testing"} for p in parts[:-1]):
                return True

        # 2. JavaScript / TypeScript
        elif ext in {".js", ".jsx", ".ts", ".tsx"}:
            if ".test." in base_name or ".spec." in base_name:
                return True
            parts = rel_lower.split("/")
            if any(p in {"__tests__", "tests", "test", "spec"} for p in parts[:-1]):
                return True

        # 3. Java
        elif ext == ".java":
            if (
                base_name.endswith("test.java")
                or base_name.endswith("tests.java")
                or base_name.endswith("testcase.java")
                or base_name.startswith("test")
            ):
                return True
            if "src/test/java/" in rel_lower or "test/" in rel_lower:
                return True

        # 4. Go
        elif ext == ".go":
            if base_name.endswith("_test.go"):
                return True

        return False

    @classmethod
    def _detect_frameworks(
        cls, repo_dir: str, scanned_files: List[str]
    ) -> Set[str]:
        """Statically inspects import statements and source text for test framework footprints."""
        frameworks: Set[str] = set()

        re_py_frameworks = re.compile(
            r"^\s*(?:import|from)\s+(pytest|unittest|doctest|hypothesis)\b",
            re.MULTILINE,
        )
        re_js_frameworks = re.compile(
            r"['\"](vitest|jest|@jest/globals|mocha|chai|cypress|playwright)['\"]",
            re.MULTILINE,
        )
        re_java_frameworks = re.compile(
            r"import\s+(?:static\s+)?(org\.junit|org\.testng|org\.assertj)\b",
            re.MULTILINE,
        )
        re_go_frameworks = re.compile(
            r"import\s+.*[\"'](testing|github\.com/stretchr/testify(?:\/\w+)*)[\"']",
            re.MULTILINE,
        )

        for rel_file in scanned_files:
            _, ext = os.path.splitext(rel_file.lower())
            if ext in cls.DOC_EXTENSIONS:
                continue

            abs_path = os.path.join(repo_dir, rel_file)
            try:
                if os.path.getsize(abs_path) > RepositoryStorageService.MAX_FILE_READ_SIZE_BYTES:
                    continue
                with open(abs_path, "rb") as f:
                    raw_bytes = f.read()
                if b"\x00" in raw_bytes[:1024]:
                    continue
                content = raw_bytes.decode("utf-8", errors="ignore")
            except Exception:
                continue

            # Python
            if ext == ".py":
                for m in re_py_frameworks.finditer(content):
                    frameworks.add(m.group(1))

            # JS/TS
            elif ext in {".js", ".jsx", ".ts", ".tsx"}:
                for m in re_js_frameworks.finditer(content):
                    fw = m.group(1)
                    if fw == "@jest/globals":
                        fw = "jest"
                    frameworks.add(fw)

            # Java
            elif ext == ".java":
                for m in re_java_frameworks.finditer(content):
                    pkg = m.group(1)
                    if "junit" in pkg:
                        frameworks.add("JUnit")
                    elif "testng" in pkg:
                        frameworks.add("TestNG")
                    elif "assertj" in pkg:
                        frameworks.add("AssertJ")

            # Go
            elif ext == ".go":
                for m in re_go_frameworks.finditer(content):
                    imp = m.group(1)
                    if imp == "testing":
                        frameworks.add("testing")
                    elif "testify" in imp:
                        frameworks.add("testify")

        return frameworks

    @classmethod
    def _count_assertions_and_functions(
        cls, file_text: str, ext: str
    ) -> Tuple[int, int]:
        """Statically counts assertion calls and test function occurrences in a test file."""
        assertion_count = 0
        test_fn_count = 0

        # Regex assertion patterns
        re_py_assert = re.compile(
            r"\bassert\b|\bself\.assert[A-Za-z0-9_]+\b|\bpytest\.raises\b"
        )
        re_js_assert = re.compile(
            r"\bexpect\(|\bassert\(|\bassert\.|\.should\."
        )
        re_java_assert = re.compile(
            r"\bassertEquals\b|\bassertTrue\b|\bassertFalse\b|\bassertThat\b|\bassertNotNull\b|\bassertNull\b|\bJUnit\.assert"
        )
        re_go_assert = re.compile(
            r"\bt\.(?:Error|Fail|Fatal|Log)(?:f)?\b|\bassert\.[A-Za-z0-9]+\b|\brequire\.[A-Za-z0-9]+\b"
        )

        # Regex test function patterns
        re_py_fn = re.compile(r"^\s*def\s+(test_[A-Za-z0-9_]+|async\s+def\s+test_[A-Za-z0-9_]+)\b", re.MULTILINE)
        re_js_fn = re.compile(r"\b(?:it|test|describe|suite)\s*\(", re.MULTILINE)
        re_java_fn = re.compile(r"@(Test|ParameterizedTest)\b|def\s+test[A-Za-z0-9_]*\(|public\s+void\s+test[A-Za-z0-9_]*\(", re.MULTILINE)
        re_go_fn = re.compile(r"^\s*func\s+(Test|Benchmark|Fuzz)[A-Za-z0-9_]*\(", re.MULTILINE)

        lines = file_text.splitlines()

        for line in lines:
            if cls._is_comment_line(line):
                continue

            # Assertion matching
            if ext == ".py":
                assertion_count += len(re_py_assert.findall(line))
            elif ext in {".js", ".jsx", ".ts", ".tsx"}:
                assertion_count += len(re_js_assert.findall(line))
            elif ext == ".java":
                assertion_count += len(re_java_assert.findall(line))
            elif ext == ".go":
                assertion_count += len(re_go_assert.findall(line))

        # Test function count matching (multi-line context / file text)
        if ext == ".py":
            test_fn_count = len(re_py_fn.findall(file_text))
        elif ext in {".js", ".jsx", ".ts", ".tsx"}:
            test_fn_count = len(re_js_fn.findall(file_text))
        elif ext == ".java":
            test_fn_count = len(re_java_fn.findall(file_text))
        elif ext == ".go":
            test_fn_count = len(re_go_fn.findall(file_text))

        return assertion_count, test_fn_count

    @classmethod
    def _compute_source_mapping(
        cls, source_file: str, test_files: List[str]
    ) -> SourceTestMapping:
        """Determines heuristic mapping between a source file and potential test files."""
        src_base = os.path.basename(source_file).lower()
        src_stem, _ = os.path.splitext(src_base)
        src_clean_stem = src_stem.replace("_", "").replace("-", "").replace(".", "")

        best_match: Optional[str] = None
        best_confidence = "NONE"

        for test_file in test_files:
            test_base = os.path.basename(test_file).lower()
            test_stem, _ = os.path.splitext(test_base)
            test_clean_stem = test_stem.replace("_", "").replace("-", "").replace(".", "")

            # Exact match conventions
            # Python: test_service.py <-> service.py or service_test.py <-> service.py
            if test_base == f"test_{src_base}" or test_base == f"{src_stem}_test.py":
                best_match = test_file
                best_confidence = "HIGH"
                break
            # JS/TS: service.test.ts <-> service.ts or service.spec.ts <-> service.ts
            elif test_base in {f"{src_stem}.test.ts", f"{src_stem}.spec.ts", f"{src_stem}.test.js", f"{src_stem}.spec.js", f"{src_stem}.test.tsx", f"{src_stem}.spec.tsx", f"{src_stem}.test.jsx", f"{src_stem}.spec.jsx"}:
                best_match = test_file
                best_confidence = "HIGH"
                break
            # Java: ServiceTest.java <-> Service.java
            elif test_base in {f"{src_stem}test.java", f"{src_stem}tests.java", f"{src_stem}testcase.java", f"test{src_stem}.java"}:
                best_match = test_file
                best_confidence = "HIGH"
                break
            # Go: service_test.go <-> service.go
            elif test_base == f"{src_stem}_test.go":
                best_match = test_file
                best_confidence = "HIGH"
                break

            # Secondary Heuristics (Partial Stem Matching)
            if best_confidence != "HIGH":
                if src_clean_stem in test_clean_stem:
                    best_match = test_file
                    best_confidence = "MEDIUM"

        return SourceTestMapping(
            source_file=source_file,
            has_obvious_test=best_match is not None,
            matching_test_file=best_match,
            confidence=best_confidence,
        )

    @classmethod
    def analyze_repository_testing(cls, repo_id: str) -> RepositoryTestingResponse:
        """
        Statically evaluates testing metrics, framework footprints, and coverage signals across stored repo files.

        Args:
            repo_id: Unique repository identifier.

        Returns:
            RepositoryTestingResponse: Aggregated testing intelligence data.
        """
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        # 1. Reuse Scanner & Symbol Extractor
        scan_result = RepositoryScanner.scan_extracted_directory(repo_dir)
        extracted_symbols_resp = CodeIntelligenceService.extract_repository_symbols(repo_id)

        all_scanned = scan_result.scanned_files
        all_dirs = scan_result.directories

        test_files_summary: List[TestFileSummary] = []
        findings: List[TestingFindingItem] = []
        source_mappings: List[SourceTestMapping] = []

        test_file_paths: List[str] = []
        source_file_paths: List[str] = []
        detected_test_dirs: Set[str] = set()

        total_assertions = 0
        total_test_functions = 0
        finding_id_counter = 1

        # 2. Framework Detection
        frameworks_set = cls._detect_frameworks(repo_dir, all_scanned)
        frameworks_list = sorted(list(frameworks_set))

        for fw in frameworks_list:
            findings.append(
                TestingFindingItem(
                    id=f"tst-{finding_id_counter}",
                    file_path="repository",
                    rule_id="TEST_FRAMEWORK_DETECTED",
                    rule_name="Test Framework Identified",
                    category="framework",
                    classification="VERIFIED_STATIC_FACT",
                    severity="INFO",
                    message=f"Static evidence indicates usage of the '{fw}' testing framework.",
                    line_start=1,
                    line_end=1,
                    evidence=f"Framework import footprint: {fw}",
                    remediation="Maintain existing test framework setup and execution tooling.",
                )
            )
            finding_id_counter += 1

        # Identify Test Directories
        for d in all_dirs:
            d_lower = d.lower().replace("\\", "/")
            parts = d_lower.split("/")
            if any(p in {"tests", "test", "testing", "__tests__", "spec"} for p in parts):
                detected_test_dirs.add(d)

        # 3. Classify Test Files vs Source Files
        for rel_path in all_scanned:
            base_name = os.path.basename(rel_path).lower()
            _, ext = os.path.splitext(rel_path.lower())

            if ext in cls.DOC_EXTENSIONS or "readme" in base_name or "license" in base_name:
                continue

            abs_path = os.path.join(repo_dir, rel_path)

            if cls._is_test_file(rel_path):
                test_file_paths.append(rel_path)

                # Read test file content safely
                file_text = ""
                try:
                    if os.path.getsize(abs_path) <= RepositoryStorageService.MAX_FILE_READ_SIZE_BYTES:
                        with open(abs_path, "rb") as f:
                            raw_bytes = f.read()
                        if b"\x00" not in raw_bytes[:1024]:
                            file_text = raw_bytes.decode("utf-8", errors="ignore")
                except Exception:
                    pass

                assertions, test_fns = cls._count_assertions_and_functions(file_text, ext)
                total_assertions += assertions
                total_test_functions += test_fns

                # Framework per test file
                fw_name = "unknown"
                for fw in frameworks_list:
                    if fw.lower() in file_text.lower() or fw.lower() in ext:
                        fw_name = fw
                        break
                if fw_name == "unknown" and frameworks_list:
                    fw_name = frameworks_list[0]

                lang_name = ext.lstrip(".").upper()
                if ext == ".py":
                    lang_name = "Python"
                elif ext in {".ts", ".tsx"}:
                    lang_name = "TypeScript"
                elif ext in {".js", ".jsx"}:
                    lang_name = "JavaScript"
                elif ext == ".java":
                    lang_name = "Java"
                elif ext == ".go":
                    lang_name = "Go"

                test_files_summary.append(
                    TestFileSummary(
                        file_path=rel_path,
                        language=lang_name,
                        framework=fw_name,
                        test_function_count=test_fns,
                        assertion_count=assertions,
                    )
                )

                # Rule 1: TEST_FILE_DETECTED
                findings.append(
                    TestingFindingItem(
                        id=f"tst-{finding_id_counter}",
                        file_path=rel_path,
                        rule_id="TEST_FILE_DETECTED",
                        rule_name="Test File Identified",
                        category="inventory",
                        classification="VERIFIED_STATIC_FACT",
                        severity="INFO",
                        message=f"Test file detected containing {test_fns} test functions and {assertions} assertions.",
                        line_start=1,
                        line_end=1,
                        evidence=f"File naming pattern: {os.path.basename(rel_path)}",
                        remediation="Ensure test functions remain maintained and execute cleanly in CI environment.",
                    )
                )
                finding_id_counter += 1

                # Rule 2: TEST_SUITE_WITHOUT_ASSERTIONS
                if test_fns > 0 and assertions == 0:
                    findings.append(
                        TestingFindingItem(
                            id=f"tst-{finding_id_counter}",
                            file_path=rel_path,
                            rule_id="TEST_SUITE_WITHOUT_ASSERTIONS",
                            rule_name="Test File Lacks Recognized Assertions",
                            category="quality",
                            classification="HEURISTIC_TESTING_SIGNAL",
                            severity="MEDIUM",
                            message="Static inspection detected test functions but no recognized assertion calls (e.g. assert, expect).",
                            line_start=1,
                            line_end=1,
                            evidence="Test function count > 0, assertion count = 0",
                            remediation="Verify that test cases include explicit validation assertions rather than empty or print-only test bodies.",
                        )
                    )
                    finding_id_counter += 1
            else:
                # Only include source code files in source_file_paths
                if ext in {".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go"}:
                    source_file_paths.append(rel_path)

        # 4. Source-to-Test Mapping Heuristics & Source Coverage Signals
        source_files_with_tests = 0
        source_files_without_tests = 0

        for src_path in source_file_paths:
            mapping = cls._compute_source_mapping(src_path, test_file_paths)
            source_mappings.append(mapping)

            if mapping.has_obvious_test:
                source_files_with_tests += 1
            else:
                source_files_without_tests += 1

                # Rule 3: SOURCE_FILE_WITHOUT_OBVIOUS_TEST
                findings.append(
                    TestingFindingItem(
                        id=f"tst-{finding_id_counter}",
                        file_path=src_path,
                        rule_id="SOURCE_FILE_WITHOUT_OBVIOUS_TEST",
                        rule_name="Source File Without Obvious Matching Test",
                        category="coverage_gap",
                        classification="HEURISTIC_TESTING_SIGNAL",
                        severity="LOW",
                        message="No obvious matching test file detected for this source file using standard naming conventions.",
                        line_start=1,
                        line_end=1,
                        evidence=f"Source file stem: '{os.path.splitext(os.path.basename(src_path))[0]}'",
                        remediation="Consider adding a dedicated unit test suite for this module (e.g. test_<name>.py or <name>.test.ts).",
                    )
                )
                finding_id_counter += 1

        # 5. Public Function Symbol Inspection
        for file_syms in extracted_symbols_resp.file_symbols:
            if cls._is_test_file(file_syms.file_path):
                continue

            # If source file has no obvious test file, flag public functions
            has_matching_test = any(
                m.source_file == file_syms.file_path and m.has_obvious_test
                for m in source_mappings
            )
            if not has_matching_test:
                for sym in file_syms.symbols:
                    if sym.kind in {"function", "method"} and sym.visibility in {"public", None}:
                        if not sym.name.startswith("_"):
                            findings.append(
                                TestingFindingItem(
                                    id=f"tst-{finding_id_counter}",
                                    file_path=file_syms.file_path,
                                    rule_id="PUBLIC_FUNCTION_WITHOUT_OBVIOUS_TEST",
                                    rule_name="Public Function Without Obvious Test",
                                    category="coverage_gap",
                                    classification="HEURISTIC_TESTING_SIGNAL",
                                    severity="LOW",
                                    message=f"Public function '{sym.name}' has no obvious matching test function in repository.",
                                    line_start=sym.line_start,
                                    line_end=sym.line_end,
                                    evidence=f"Function signature: {sym.signature or sym.name}",
                                    remediation=f"Add unit test coverage verifying '{sym.name}' input validation and execution paths.",
                                )
                            )
                            finding_id_counter += 1

        # Compute Metrics
        total_source_files = len(source_file_paths)
        estimated_test_ratio = 0.0
        if total_source_files > 0:
            estimated_test_ratio = round(
                (source_files_with_tests / total_source_files) * 100.0, 2
            )

        metrics = TestingMetricsSummary(
            total_test_files=len(test_file_paths),
            total_test_functions=total_test_functions,
            total_assertions_detected=total_assertions,
            total_source_files=total_source_files,
            source_files_with_tests=source_files_with_tests,
            source_files_without_tests=source_files_without_tests,
            estimated_test_ratio=estimated_test_ratio,
            detected_frameworks=frameworks_list,
            test_directories=sorted(list(detected_test_dirs)),
        )

        # Deterministic Sorting
        findings.sort(
            key=lambda f: (
                cls.SEVERITY_ORDER.get(f.severity, 99),
                f.file_path,
                f.line_start or 0,
                f.rule_id,
            )
        )
        test_files_summary.sort(key=lambda t: t.file_path)
        source_mappings.sort(key=lambda m: m.source_file)

        return RepositoryTestingResponse(
            repo_id=repo_id,
            metrics=metrics,
            test_files=test_files_summary,
            source_mappings=source_mappings,
            findings=findings,
        )

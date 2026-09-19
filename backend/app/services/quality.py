"""
Code Quality Intelligence Service.

Purpose:
Evaluates deterministic code quality rules against AST symbol metadata, file line counts,
and dependency relationships without using AI, SAST/security scanners, or running code.
"""

import os
import uuid
from typing import Dict, List, Set

from app.schemas.quality import (
    FileQualitySummary,
    QualityFindingItem,
    QualityMetricsSummary,
    RepositoryQualityResponse,
)
from app.schemas.symbols import SymbolItem, SymbolKind
from app.services.dependency import CodeDependencyService
from app.services.parser.service import CodeIntelligenceService
from app.services.scanner import RepositoryScanner
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService


class CodeQualityService:
    """Service for deterministic code quality analysis."""

    SEVERITY_ORDER: Dict[str, int] = {
        "HIGH": 0,
        "MEDIUM": 1,
        "LOW": 2,
    }

    @classmethod
    def analyze_repository_quality(cls, repo_id: str) -> RepositoryQualityResponse:
        """
        Statically evaluates codebase quality rules and metrics.

        Args:
            repo_id: Unique repository identifier.

        Returns:
            RepositoryQualityResponse: Aggregated findings and summary metrics.

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

        # 2. Reuse Symbol Intelligence Service
        symbols_res = CodeIntelligenceService.extract_repository_symbols(repo_id)

        # Map file_path -> List[SymbolItem]
        file_symbols_map: Dict[str, List[SymbolItem]] = {}
        for file_sym in symbols_res.file_symbols:
            file_symbols_map[file_sym.file_path] = file_sym.symbols

        # 3. Reuse Dependency Intelligence Service
        dep_res = CodeDependencyService.analyze_repository_dependencies(repo_id)

        # Build circular dependency files set
        circular_files_set: Set[str] = set()
        if dep_res.has_circular_dependencies and dep_res.circular_dependency_cycles:
            for cycle in dep_res.circular_dependency_cycles:
                for file_path in cycle:
                    circular_files_set.add(file_path)

        # 4. Count lines for all scanned text files
        file_lines_map: Dict[str, int] = {}
        all_file_paths: Set[str] = set(scan_result.scanned_files)
        all_file_paths.update(file_symbols_map.keys())

        for rel_path in all_file_paths:
            abs_path = os.path.join(repo_dir, rel_path)
            lines_count = 0
            if os.path.exists(abs_path) and os.path.isfile(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines_count = sum(1 for _ in f)
                except Exception:
                    lines_count = 0
            file_lines_map[rel_path] = lines_count

        # 5. Evaluate Quality Rules
        findings: List[QualityFindingItem] = []
        finding_id_counter = 1

        # Track metrics
        total_functions_count = 0
        total_function_span_sum = 0
        total_parameters_sum = 0
        public_symbols_count = 0
        public_symbols_with_docstring = 0

        # RULE 4: VERY_LONG_FILE
        for file_path, total_lines in file_lines_map.items():
            if total_lines > 500:
                severity = "HIGH" if total_lines > 1000 else "MEDIUM"
                findings.append(
                    QualityFindingItem(
                        id=f"qual-{finding_id_counter}",
                        file_path=file_path,
                        rule_id="VERY_LONG_FILE",
                        rule_name="Very Long File",
                        category="maintainability",
                        severity=severity,
                        finding_type="HEURISTIC_RISK",
                        message=f"File spans {total_lines} lines, exceeding the threshold of 500 lines.",
                        line_start=1,
                        line_end=total_lines,
                        symbol_name=None,
                        metric_value=float(total_lines),
                        threshold_value=500.0,
                    )
                )
                finding_id_counter += 1

        # Evaluate Symbol-based Rules (1, 2, 3, 5)
        for file_path, symbols in file_symbols_map.items():
            # Class method counts map for Rule 3
            class_method_counts: Dict[str, int] = {}
            for sym in symbols:
                if sym.parent_symbol and sym.kind in (
                    SymbolKind.METHOD,
                    SymbolKind.FUNCTION,
                ):
                    class_method_counts[sym.parent_symbol] = (
                        class_method_counts.get(sym.parent_symbol, 0) + 1
                    )

            for sym in symbols:
                # Function & Method metrics calculation
                if sym.kind in (
                    SymbolKind.FUNCTION,
                    SymbolKind.METHOD,
                ):
                    total_functions_count += 1
                    func_span = (
                        (sym.line_end - sym.line_start + 1)
                        if (sym.line_end and sym.line_end >= sym.line_start)
                        else 1
                    )
                    total_function_span_sum += func_span

                    param_count = (
                        len(sym.parameters) if sym.parameters is not None else 0
                    )
                    total_parameters_sum += param_count

                    # RULE 1: LONG_FUNCTION (> 50 lines)
                    if func_span > 50:
                        findings.append(
                            QualityFindingItem(
                                id=f"qual-{finding_id_counter}",
                                file_path=file_path,
                                rule_id="LONG_FUNCTION",
                                rule_name="Long Function / Method",
                                category="complexity",
                                severity="MEDIUM",
                                finding_type="HEURISTIC_RISK",
                                message=f"Function '{sym.name}' spans {func_span} lines, exceeding the threshold of 50 lines.",
                                line_start=sym.line_start,
                                line_end=sym.line_end,
                                symbol_name=sym.name,
                                metric_value=float(func_span),
                                threshold_value=50.0,
                            )
                        )
                        finding_id_counter += 1

                    # RULE 2: EXCESSIVE_PARAMETERS (> 5 params)
                    if param_count > 5:
                        findings.append(
                            QualityFindingItem(
                                id=f"qual-{finding_id_counter}",
                                file_path=file_path,
                                rule_id="EXCESSIVE_PARAMETERS",
                                rule_name="Excessive Parameters",
                                category="maintainability",
                                severity="MEDIUM",
                                finding_type="HEURISTIC_RISK",
                                message=f"Function '{sym.name}' accepts {param_count} parameters, exceeding the threshold of 5 parameters.",
                                line_start=sym.line_start,
                                line_end=sym.line_end,
                                symbol_name=sym.name,
                                metric_value=float(param_count),
                                threshold_value=5.0,
                            )
                        )
                        finding_id_counter += 1

                # RULE 3: LARGE_CLASS (> 300 lines OR > 15 methods)
                if sym.kind == SymbolKind.CLASS:
                    class_span = (
                        (sym.line_end - sym.line_start + 1)
                        if (sym.line_end and sym.line_end >= sym.line_start)
                        else 1
                    )
                    method_count = class_method_counts.get(sym.name, 0)

                    if class_span > 300 or method_count > 15:
                        findings.append(
                            QualityFindingItem(
                                id=f"qual-{finding_id_counter}",
                                file_path=file_path,
                                rule_id="LARGE_CLASS",
                                rule_name="Large Class",
                                category="complexity",
                                severity="MEDIUM",
                                finding_type="HEURISTIC_RISK",
                                message=f"Class '{sym.name}' spans {class_span} lines (threshold: 300) or contains {method_count} methods (threshold: 15).",
                                line_start=sym.line_start,
                                line_end=sym.line_end,
                                symbol_name=sym.name,
                                metric_value=float(max(class_span, method_count)),
                                threshold_value=300.0 if class_span > 300 else 15.0,
                            )
                        )
                        finding_id_counter += 1

                # RULE 5: MISSING_DOCSTRING (public symbols)
                if sym.kind in (
                    SymbolKind.FUNCTION,
                    SymbolKind.CLASS,
                    SymbolKind.METHOD,
                ):
                    is_public = (
                        sym.visibility == "public"
                        or (
                            (sym.visibility is None or sym.visibility == "")
                            and not sym.name.startswith("_")
                        )
                    )
                    if is_public:
                        public_symbols_count += 1
                        has_docstring = bool(sym.docstring and sym.docstring.strip())
                        if has_docstring:
                            public_symbols_with_docstring += 1
                        else:
                            findings.append(
                                QualityFindingItem(
                                    id=f"qual-{finding_id_counter}",
                                    file_path=file_path,
                                    rule_id="MISSING_DOCSTRING",
                                    rule_name="Missing Docstring",
                                    category="documentation",
                                    severity="LOW",
                                    finding_type="VERIFIED_FACT",
                                    message=f"Public symbol '{sym.name}' is missing a docstring.",
                                    line_start=sym.line_start,
                                    line_end=sym.line_end,
                                    symbol_name=sym.name,
                                    metric_value=0.0,
                                    threshold_value=1.0,
                                )
                            )
                            finding_id_counter += 1

        # RULE 6: CIRCULAR_DEPENDENCY
        for file_path in sorted(list(circular_files_set)):
            findings.append(
                QualityFindingItem(
                    id=f"qual-{finding_id_counter}",
                    file_path=file_path,
                    rule_id="CIRCULAR_DEPENDENCY",
                    rule_name="Circular Dependency Participation",
                    category="architecture",
                    severity="HIGH",
                    finding_type="VERIFIED_FACT",
                    message=f"File '{file_path}' participates in a circular dependency cycle.",
                    line_start=1,
                    line_end=None,
                    symbol_name=None,
                    metric_value=None,
                    threshold_value=None,
                )
            )
            finding_id_counter += 1

        # RULE 7: UNRESOLVED_IMPORT
        for dep in dep_res.dependencies:
            if dep.resolution_status == "unresolved":
                findings.append(
                    QualityFindingItem(
                        id=f"qual-{finding_id_counter}",
                        file_path=dep.source_file,
                        rule_id="UNRESOLVED_IMPORT",
                        rule_name="Unresolved Import",
                        category="architecture",
                        severity="MEDIUM",
                        finding_type="VERIFIED_FACT",
                        message=f"File '{dep.source_file}' contains unresolved import '{dep.raw_import}'.",
                        line_start=dep.line_number,
                        line_end=dep.line_number,
                        symbol_name=dep.raw_import,
                        metric_value=None,
                        threshold_value=None,
                    )
                )
                finding_id_counter += 1

        # Deterministic Finding Ordering: severity (HIGH -> MEDIUM -> LOW), file_path, line_start, rule_id
        findings.sort(
            key=lambda f: (
                cls.SEVERITY_ORDER.get(f.severity, 99),
                f.file_path,
                f.line_start or 0,
                f.rule_id,
            )
        )

        # 6. Build Summary Metrics
        high_cnt = sum(1 for f in findings if f.severity == "HIGH")
        med_cnt = sum(1 for f in findings if f.severity == "MEDIUM")
        low_cnt = sum(1 for f in findings if f.severity == "LOW")

        doc_cov = (
            round((public_symbols_with_docstring / public_symbols_count) * 100.0, 1)
            if public_symbols_count > 0
            else 100.0
        )

        avg_func_len = (
            round(total_function_span_sum / total_functions_count, 1)
            if total_functions_count > 0
            else 0.0
        )

        avg_params = (
            round(total_parameters_sum / total_functions_count, 1)
            if total_functions_count > 0
            else 0.0
        )

        large_files_cnt = sum(1 for lines in file_lines_map.values() if lines > 500)
        long_funcs_cnt = sum(1 for f in findings if f.rule_id == "LONG_FUNCTION")

        summary = QualityMetricsSummary(
            total_findings=len(findings),
            high_severity_count=high_cnt,
            medium_severity_count=med_cnt,
            low_severity_count=low_cnt,
            documentation_coverage_percentage=doc_cov,
            average_function_length=avg_func_len,
            average_parameters_per_function=avg_params,
            large_files_count=large_files_cnt,
            long_functions_count=long_funcs_cnt,
        )

        # 7. Build File Quality Summaries
        # Count findings per file
        file_findings_count_map: Dict[str, int] = {}
        for f in findings:
            file_findings_count_map[f.file_path] = (
                file_findings_count_map.get(f.file_path, 0) + 1
            )

        files_summary: List[FileQualitySummary] = []
        for file_path in sorted(list(all_file_paths)):
            lang = RepositoryScanner.detect_language(file_path)
            total_l = file_lines_map.get(file_path, 0)
            syms_cnt = len(file_symbols_map.get(file_path, []))
            finds_cnt = file_findings_count_map.get(file_path, 0)

            files_summary.append(
                FileQualitySummary(
                    file_path=file_path,
                    language=lang,
                    total_lines=total_l,
                    total_symbols=syms_cnt,
                    findings_count=finds_cnt,
                )
            )

        # Sort files_summary by findings_count descending, then file_path
        files_summary.sort(key=lambda f: (-f.findings_count, f.file_path))

        return RepositoryQualityResponse(
            repo_id=repo_id,
            summary=summary,
            findings=findings,
            files_summary=files_summary,
        )

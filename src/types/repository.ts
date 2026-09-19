/**
 * TypeScript types and interfaces for Repository Explorer and Scan Results.
 */

export interface RepositoryScanResult {
  total_files: number;
  detected_languages: Record<string, number>;
  directories: string[];
  scanned_files: string[];
}

export interface RepositoryUploadResponse {
  filename: string;
  size: number;
  status: string;
  message: string;
  repo_id?: string;
  scan_result?: RepositoryScanResult;
}

export interface RepositoryFileContentResponse {
  repo_id: string;
  path: string;
  size: number;
  content: string;
  encoding: string;
}

export type SymbolKind = 'function' | 'class' | 'method' | 'import';

export interface SymbolItem {
  name: string;
  kind: SymbolKind;
  file_path: string;
  line_start: number;
  line_end: number;
  signature?: string;
  docstring?: string;
  parent_symbol?: string | null;
  parameters?: string[] | null;
  return_type?: string | null;
  visibility?: string | null;
}

export interface FileSymbols {
  file_path: string;
  language: string;
  symbols: SymbolItem[];
}

export interface RepositorySymbolsResponse {
  repo_id: string;
  total_symbols: number;
  file_symbols: FileSymbols[];
}

export interface FileNode {
  type: 'file';
  name: string;
  path: string;
  extension: string;
}

export interface FolderNode {
  type: 'folder';
  name: string;
  path: string;
  children: Array<FileNode | FolderNode>;
}

export type TreeNode = FileNode | FolderNode;

export interface SearchResultItem {
  file_path: string;
  line_number: number;
  line_content: string;
  match_start: number;
  match_end: number;
}

export interface RepositorySearchResponse {
  repo_id: string;
  query: string;
  total_matches: number;
  total_files_searched: number;
  matches: SearchResultItem[];
}

export interface SearchOptions {
  case_sensitive?: boolean;
  max_results?: number;
  file_extension?: string;
}

export type DependencyType = 'internal' | 'external' | 'unknown';
export type ResolutionStatus = 'resolved' | 'external' | 'unresolved';

export interface DependencyItem {
  source_file: string;
  target_file?: string | null;
  raw_import: string;
  module_name: string;
  imported_symbols: string[];
  dependency_type: DependencyType;
  resolution_status: ResolutionStatus;
  line_number: number;
}

export interface RepositoryDependenciesResponse {
  repo_id: string;
  total_files: number;
  total_dependencies: number;
  internal_dependencies_count: number;
  external_dependencies_count: number;
  unresolved_dependencies_count: number;
  has_circular_dependencies: boolean;
  circular_dependency_cycles: string[][];
  dependencies: DependencyItem[];
}

export interface ModuleDocItem {
  file_path: string;
  language: string;
  summary_docstring?: string | null;
  total_symbols: number;
  public_symbols_count: number;
  symbols: SymbolItem[];
  imports_count: number;
  imported_by_count: number;
}

export interface OverviewDocSummary {
  repo_id: string;
  total_files: number;
  total_symbols: number;
  detected_languages: Record<string, number>;
  readme_file_path?: string | null;
  readme_content?: string | null;
}

export interface ArchitectureDocSummary {
  total_internal_dependencies: number;
  external_packages: string[];
  has_circular_dependencies: boolean;
  circular_cycles_count: number;
}

export interface RepositoryDocumentationResponse {
  repo_id: string;
  overview: OverviewDocSummary;
  architecture: ArchitectureDocSummary;
  modules: ModuleDocItem[];
}

export interface QualityFindingItem {
  id: string;
  file_path: string;
  rule_id: string;
  rule_name: string;
  category: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  finding_type: 'VERIFIED_FACT' | 'HEURISTIC_RISK';
  message: string;
  line_start?: number | null;
  line_end?: number | null;
  symbol_name?: string | null;
  metric_value?: number | null;
  threshold_value?: number | null;
}

export interface QualityMetricsSummary {
  total_findings: number;
  high_severity_count: number;
  medium_severity_count: number;
  low_severity_count: number;
  documentation_coverage_percentage: number;
  average_function_length: number;
  average_parameters_per_function: number;
  large_files_count: number;
  long_functions_count: number;
}

export interface FileQualitySummary {
  file_path: string;
  language: string;
  total_lines: number;
  total_symbols: number;
  findings_count: number;
}

export interface RepositoryQualityResponse {
  repo_id: string;
  summary: QualityMetricsSummary;
  findings: QualityFindingItem[];
  files_summary: FileQualitySummary[];
}







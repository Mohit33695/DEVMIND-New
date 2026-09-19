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




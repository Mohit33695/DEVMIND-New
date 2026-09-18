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
  scan_result?: RepositoryScanResult;
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

/**
 * Pure file-tree builder utility.
 * Transforms flat relative file path arrays into a hierarchical tree of FolderNode and FileNode instances.
 */

import type { FileNode, FolderNode, TreeNode } from '@/types/repository';

/**
 * Builds a hierarchical tree structure from a list of relative file paths.
 *
 * @param scannedFiles Array of relative file paths (e.g. ['src/index.ts', 'README.md'])
 * @param rootName Optional name for the root folder container (defaults to 'root')
 * @returns Root FolderNode containing nested folder and file nodes.
 */
export function buildFileTree(scannedFiles: string[], rootName: string = 'root'): FolderNode {
  const rootNode: FolderNode = {
    type: 'folder',
    name: rootName,
    path: '',
    children: [],
  };

  for (const rawPath of scannedFiles) {
    if (!rawPath || !rawPath.trim()) continue;

    const normalizedPath = rawPath.replace(/\\/g, '/');
    const parts = normalizedPath.split('/').filter(Boolean);

    let currentFolder = rootNode;
    let currentPath = '';

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isFile = i === parts.length - 1;

      currentPath = currentPath ? `${currentPath}/${part}` : part;

      if (isFile) {
        const dotIndex = part.lastIndexOf('.');
        const extension = dotIndex > -1 ? part.substring(dotIndex).toLowerCase() : '';

        // Prevent duplicate file nodes
        const existingFile = currentFolder.children.find(
          (child): child is FileNode => child.type === 'file' && child.name === part
        );

        if (!existingFile) {
          const fileNode: FileNode = {
            type: 'file',
            name: part,
            path: currentPath,
            extension,
          };
          currentFolder.children.push(fileNode);
        }
      } else {
        // Look for existing child folder
        let existingFolder = currentFolder.children.find(
          (child): child is FolderNode => child.type === 'folder' && child.name === part
        );

        if (!existingFolder) {
          existingFolder = {
            type: 'folder',
            name: part,
            path: currentPath,
            children: [],
          };
          currentFolder.children.push(existingFolder);
        }
        currentFolder = existingFolder;
      }
    }
  }

  // Helper function to recursively sort nodes: Folders first (A-Z), then Files (A-Z)
  function sortNodes(folder: FolderNode): void {
    folder.children.sort((a: TreeNode, b: TreeNode) => {
      if (a.type !== b.type) {
        return a.type === 'folder' ? -1 : 1;
      }
      return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
    });

    for (const child of folder.children) {
      if (child.type === 'folder') {
        sortNodes(child);
      }
    }
  }

  sortNodes(rootNode);
  return rootNode;
}

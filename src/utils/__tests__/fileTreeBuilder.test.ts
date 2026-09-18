/**
 * Unit tests for pure fileTreeBuilder utility.
 * Verifies tree construction for nested folders, root files, multiple files per directory, and sorting.
 */

import { buildFileTree } from '../fileTreeBuilder';
import type { FileNode, FolderNode } from '../../types/repository';

export function runFileTreeBuilderTests() {
  console.log('Running buildFileTree tests...');

  // 1. Root-level files test
  const rootFiles = ['README.md', 'package.json', 'Dockerfile'];
  const rootTree = buildFileTree(rootFiles, 'my-repo');
  console.assert(rootTree.name === 'my-repo', 'Root tree should have rootName');
  console.assert(rootTree.children.length === 3, 'Should contain 3 root files');
  console.assert(rootTree.children[0].name === 'Dockerfile', 'Dockerfile sorted first');
  console.assert(rootTree.children[1].name === 'package.json', 'package.json sorted second');
  console.assert(rootTree.children[2].name === 'README.md', 'README.md sorted third');

  // 2. Nested folders test
  const nestedFiles = [
    'src/components/UploadCard.tsx',
    'src/components/Header.tsx',
    'src/index.ts',
    'backend/app/main.py',
    'backend/requirements.txt',
    'README.md',
  ];

  const tree = buildFileTree(nestedFiles, 'repo');

  // Folders first: backend, src, then file: README.md
  console.assert(tree.children.length === 3, 'Root should have 2 folders and 1 file');
  const backendFolder = tree.children[0] as FolderNode;
  const srcFolder = tree.children[1] as FolderNode;
  const readmeFile = tree.children[2] as FileNode;

  console.assert(backendFolder.type === 'folder' && backendFolder.name === 'backend', 'backend folder first');
  console.assert(srcFolder.type === 'folder' && srcFolder.name === 'src', 'src folder second');
  console.assert(readmeFile.type === 'file' && readmeFile.name === 'README.md', 'README.md file third');

  // Check nested hierarchy in backend
  console.assert(backendFolder.children.length === 2, 'backend should contain app folder and requirements.txt');
  const appFolder = backendFolder.children[0] as FolderNode;
  const reqFile = backendFolder.children[1] as FileNode;
  console.assert(appFolder.name === 'app' && appFolder.type === 'folder', 'app is nested folder in backend');
  console.assert(reqFile.name === 'requirements.txt' && reqFile.type === 'file', 'requirements.txt in backend');

  const mainPy = appFolder.children[0] as FileNode;
  console.assert(mainPy.name === 'main.py' && mainPy.path === 'backend/app/main.py', 'main.py path correct');

  // Check nested hierarchy in src
  console.assert(srcFolder.children.length === 2, 'src contains components folder and index.ts');
  const componentsFolder = srcFolder.children[0] as FolderNode;
  console.assert(componentsFolder.children.length === 2, 'components folder contains 2 files');
  console.assert(componentsFolder.children[0].name === 'Header.tsx', 'Header.tsx sorted first');
  console.assert(componentsFolder.children[1].name === 'UploadCard.tsx', 'UploadCard.tsx sorted second');

  console.log('All buildFileTree tests passed successfully!');
}

runFileTreeBuilderTests();


import React, { useState, useEffect, useMemo } from 'react';
import type {
  RepositoryScanResult,
  TreeNode,
  RepositoryFileContentResponse,
  RepositorySymbolsResponse,
  SymbolItem,
} from '@/types/repository';
import { buildFileTree } from '@/utils/fileTreeBuilder';
import { fetchFileContent, fetchRepositorySymbols } from '@/api/client';
import { FileViewer } from '@/components/repository/FileViewer';
import { SymbolPanel } from '@/components/repository/SymbolPanel';

interface RepositoryExplorerProps {
  scanResult: RepositoryScanResult;
  filename?: string;
  repoId?: string;
}

export const RepositoryExplorer: React.FC<RepositoryExplorerProps> = ({
  scanResult,
  filename,
  repoId,
}) => {
  const rootFolderName = filename ? filename.replace(/\.zip$/i, '') : 'repository';

  // Build hierarchical file tree from flat path list
  const rootNode = useMemo(
    () => buildFileTree(scanResult.scanned_files, rootFolderName),
    [scanResult.scanned_files, rootFolderName]
  );

  // Expanded folders state (all top-level folders expanded by default)
  const [expandedPaths, setExpandedPaths] = useState<Record<string, boolean>>(() => {
    const initialExpanded: Record<string, boolean> = { '': true };
    for (const child of rootNode.children) {
      if (child.type === 'folder') {
        initialExpanded[child.path] = true;
      }
    }
    return initialExpanded;
  });

  // Selected file & content state
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<RepositoryFileContentResponse | null>(null);
  const [isFileLoading, setIsFileLoading] = useState<boolean>(false);
  const [fileError, setFileError] = useState<string | null>(null);

  // Repository AST Symbols state
  const [repositorySymbols, setRepositorySymbols] = useState<RepositorySymbolsResponse | null>(null);
  const [isSymbolsLoading, setIsSymbolsLoading] = useState<boolean>(false);
  const [symbolsError, setSymbolsError] = useState<string | null>(null);

  // Fetch repository symbols ONCE when repoId is available
  useEffect(() => {
    if (!repoId) return;

    let isMounted = true;
    setIsSymbolsLoading(true);
    setSymbolsError(null);

    fetchRepositorySymbols(repoId)
      .then((data) => {
        if (isMounted) {
          setRepositorySymbols(data);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to fetch repository symbols.';
          setSymbolsError(msg);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsSymbolsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [repoId]);

  const toggleFolder = (path: string) => {
    setExpandedPaths((prev) => ({
      ...prev,
      [path]: !prev[path],
    }));
  };

  // Handle file selection and fetch real source content from backend
  const handleSelectFile = async (path: string) => {
    setSelectedFilePath(path);
    setSelectedFileContent(null);
    setFileError(null);

    if (!repoId) {
      setFileError('Repository ID is missing. Please re-upload the archive.');
      return;
    }

    setIsFileLoading(true);
    try {
      const contentData = await fetchFileContent(repoId, path);
      setSelectedFileContent(contentData);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to retrieve file content.';
      setFileError(errorMsg);
    } finally {
      setIsFileLoading(false);
    }
  };

  // Sort detected languages by file count descending
  const sortedLanguages = useMemo(() => {
    return Object.entries(scanResult.detected_languages || {}).sort((a, b) => b[1] - a[1]);
  }, [scanResult.detected_languages]);

  // Filter symbols for the currently selected file
  const selectedFileSymbols = useMemo<SymbolItem[]>(() => {
    if (!selectedFilePath || !repositorySymbols) return [];
    const fileMatch = repositorySymbols.file_symbols.find(
      (f) => f.file_path === selectedFilePath
    );
    return fileMatch ? fileMatch.symbols : [];
  }, [selectedFilePath, repositorySymbols]);

  return (
    <div style={styles.explorerContainer}>
      {/* 1. Repository Scan Summary Bar */}
      <div style={styles.summaryBar}>
        <div style={styles.summaryLeft}>
          <div style={styles.repoBadge}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
            <span>{rootFolderName}</span>
          </div>

          <div style={styles.metricBadge}>
            <span style={styles.metricCount}>{scanResult.total_files}</span>
            <span style={styles.metricLabel}>{scanResult.total_files === 1 ? 'file' : 'files'}</span>
          </div>

          {/* Real Backend Extracted Symbol Count Metric */}
          {repositorySymbols && (
            <div style={styles.metricBadge}>
              <span style={styles.metricCount}>{repositorySymbols.total_symbols}</span>
              <span style={styles.metricLabel}>
                {repositorySymbols.total_symbols === 1 ? 'symbol' : 'symbols'}
              </span>
            </div>
          )}
        </div>

        {/* Detected Languages Tags */}
        <div style={styles.languagesRow}>
          {sortedLanguages.map(([lang, count]) => (
            <div key={lang} style={styles.langPill}>
              <span style={styles.langDot} />
              <span style={styles.langName}>{lang}</span>
              <span style={styles.langCount}>{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 2. Side-by-Side Split View: File Tree (Left) + File Viewer & Symbol Panel (Right) */}
      <div style={styles.splitLayout}>
        {/* Left Column: File Tree Navigation */}
        <div style={styles.treeBox}>
          <div style={styles.treeHeader}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="8" y1="6" x2="21" y2="6" />
              <line x1="8" y1="12" x2="21" y2="12" />
              <line x1="8" y1="18" x2="21" y2="18" />
              <line x1="3" y1="6" x2="3.01" y2="6" />
              <line x1="3" y1="12" x2="3.01" y2="12" />
              <line x1="3" y1="18" x2="3.01" y2="18" />
            </svg>
            <span>Repository Files</span>
          </div>

          <div style={styles.treeContent}>
            {rootNode.children.length === 0 ? (
              <div style={styles.emptyTree}>No files discovered in repository scan.</div>
            ) : (
              <TreeNodeView
                node={rootNode}
                depth={0}
                expandedPaths={expandedPaths}
                onToggleFolder={toggleFolder}
                selectedFilePath={selectedFilePath}
                onSelectFile={handleSelectFile}
                isRoot={true}
              />
            )}
          </div>
        </div>

        {/* Right Column: Code Symbols Panel & Source File Viewer */}
        <div style={styles.viewerBox}>
          {selectedFilePath && (
            <SymbolPanel
              symbols={selectedFileSymbols}
              isLoading={isSymbolsLoading}
              error={symbolsError}
            />
          )}

          <FileViewer
            filePath={selectedFilePath}
            contentResponse={selectedFileContent}
            isLoading={isFileLoading}
            error={fileError}
          />
        </div>
      </div>
    </div>
  );
};

// Recursive Tree Node Renderer
interface TreeNodeViewProps {
  node: TreeNode;
  depth: number;
  expandedPaths: Record<string, boolean>;
  onToggleFolder: (path: string) => void;
  selectedFilePath: string | null;
  onSelectFile: (path: string) => void;
  isRoot?: boolean;
}

const TreeNodeView: React.FC<TreeNodeViewProps> = ({
  node,
  depth,
  expandedPaths,
  onToggleFolder,
  selectedFilePath,
  onSelectFile,
  isRoot = false,
}) => {
  if (node.type === 'folder') {
    const isExpanded = expandedPaths[node.path] ?? false;

    return (
      <div style={styles.folderNodeGroup}>
        {!isRoot && (
          <div
            role="button"
            tabIndex={0}
            style={{
              ...styles.nodeRow,
              paddingLeft: `${depth * 18 + 8}px`,
            }}
            onClick={() => onToggleFolder(node.path)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onToggleFolder(node.path);
              }
            }}
          >
            <span style={styles.chevronBox}>
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                style={{
                  transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                  transition: 'transform var(--transition-fast)',
                }}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </span>

            <span style={styles.folderIcon}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20 18a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93l-2-2H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16z" />
              </svg>
            </span>

            <span style={styles.folderName}>{node.name}</span>
            <span style={styles.childCountBadge}>({node.children.length})</span>
          </div>
        )}

        {(isRoot || isExpanded) && (
          <div style={styles.childrenGroup}>
            {node.children.map((child) => (
              <TreeNodeView
                key={child.path}
                node={child}
                depth={isRoot ? depth : depth + 1}
                expandedPaths={expandedPaths}
                onToggleFolder={onToggleFolder}
                selectedFilePath={selectedFilePath}
                onSelectFile={onSelectFile}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // File Node
  const isSelected = selectedFilePath === node.path;

  return (
    <div
      role="button"
      tabIndex={0}
      style={{
        ...styles.nodeRow,
        ...styles.fileRow,
        paddingLeft: `${depth * 18 + 24}px`,
        ...(isSelected ? styles.fileRowSelected : {}),
      }}
      onClick={() => onSelectFile(node.path)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelectFile(node.path);
        }
      }}
    >
      <span style={styles.fileIconBox}>{getFileIcon(node.extension)}</span>
      <span style={{ ...styles.fileName, ...(isSelected ? styles.fileNameSelected : {}) }}>{node.name}</span>
    </div>
  );
};

// Extension icon selector
const getFileIcon = (ext: string) => {
  switch (ext) {
    case '.ts':
    case '.tsx':
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3178C6" strokeWidth="2.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
    case '.py':
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3572A5" strokeWidth="2.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
    case '.js':
    case '.jsx':
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#EAB308" strokeWidth="2.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
    case '.json':
    case '.yaml':
    case '.yml':
    case '.toml':
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
    case '.md':
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6366F1" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
    default:
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-subtle)" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
  }
};

const styles: Record<string, React.CSSProperties> = {
  explorerContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    marginTop: '16px',
  },
  summaryBar: {
    padding: '14px 18px',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '16px',
    flexWrap: 'wrap',
  },
  summaryLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  repoBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '13.5px',
    fontWeight: 700,
    color: 'var(--color-primary)',
  },
  metricBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-main)',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    padding: '3px 10px',
    borderRadius: 'var(--radius-full)',
  },
  metricCount: {
    color: 'var(--color-primary)',
    fontWeight: 700,
  },
  metricLabel: {
    color: 'var(--text-muted)',
  },
  languagesRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  langPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '11.5px',
    fontWeight: 600,
    color: 'var(--text-main)',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-sm)',
  },
  langDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: 'var(--color-primary)',
  },
  langName: {
    fontWeight: 600,
  },
  langCount: {
    color: 'var(--text-muted)',
    fontSize: '10.5px',
  },
  splitLayout: {
    display: 'flex',
    gap: '16px',
    alignItems: 'stretch',
  },
  treeBox: {
    flex: '0 0 320px',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  viewerBox: {
    flex: 1,
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
  },
  treeHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    backgroundColor: 'var(--bg-surface)',
    borderBottom: '1px solid var(--border-default)',
    fontSize: '12px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: 'var(--text-muted)',
  },
  treeContent: {
    padding: '8px 0',
    fontFamily: 'monospace, sans-serif',
    fontSize: '13px',
    maxHeight: '520px',
    overflowY: 'auto',
    flex: 1,
  },
  emptyTree: {
    padding: '20px',
    textAlign: 'center',
    color: 'var(--text-muted)',
    fontSize: '13px',
  },
  folderNodeGroup: {
    display: 'flex',
    flexDirection: 'column',
  },
  childrenGroup: {
    display: 'flex',
    flexDirection: 'column',
  },
  nodeRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '5px 12px',
    cursor: 'pointer',
    userSelect: 'none',
    transition: 'background-color var(--transition-fast)',
    outline: 'none',
  },
  fileRow: {
    borderRadius: 'var(--radius-sm)',
    margin: '0 4px',
  },
  fileRowSelected: {
    backgroundColor: 'var(--color-primary-light)',
  },
  chevronBox: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '14px',
    height: '14px',
    color: 'var(--text-muted)',
    flexShrink: 0,
  },
  folderIcon: {
    display: 'inline-flex',
    alignItems: 'center',
    color: '#F59E0B',
    flexShrink: 0,
  },
  folderName: {
    fontWeight: 600,
    color: 'var(--text-main)',
  },
  childCountBadge: {
    fontSize: '11px',
    color: 'var(--text-subtle)',
    marginLeft: '2px',
  },
  fileIconBox: {
    display: 'inline-flex',
    alignItems: 'center',
    flexShrink: 0,
  },
  fileName: {
    color: 'var(--text-main)',
    fontWeight: 400,
  },
  fileNameSelected: {
    color: 'var(--color-primary)',
    fontWeight: 600,
  },
};

import React from 'react';
import type { RepositoryFileContentResponse } from '@/types/repository';

interface FileViewerProps {
  filePath: string | null;
  contentResponse: RepositoryFileContentResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const FileViewer: React.FC<FileViewerProps> = ({
  filePath,
  contentResponse,
  isLoading,
  error,
}) => {
  // Helper to format file byte sizes cleanly
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // 1. Unselected Empty State
  if (!filePath) {
    return (
      <div style={styles.viewerContainer}>
        <div style={styles.emptyContainer}>
          <div style={styles.emptyIconCircle}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <h4 style={styles.emptyTitle}>Select a file to inspect content</h4>
          <p style={styles.emptySubtext}>
            Click any file in the repository tree to retrieve and view its source code.
          </p>
        </div>
      </div>
    );
  }

  // 2. Loading State
  if (isLoading) {
    return (
      <div style={styles.viewerContainer}>
        <div style={styles.loadingContainer}>
          <div style={styles.spinner} />
          <span style={styles.loadingText}>Fetching content for <strong>{filePath}</strong>...</span>
        </div>
      </div>
    );
  }

  // 3. Error State
  if (error) {
    const isBinary = error.toLowerCase().includes('binary');
    const isTooLarge = error.toLowerCase().includes('exceeds') || error.toLowerCase().includes('2 mb');

    return (
      <div style={styles.viewerContainer}>
        <div style={styles.errorContainer}>
          <div style={styles.errorIconBox}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>

          <div style={styles.errorContent}>
            <h4 style={styles.errorTitle}>
              {isBinary
                ? 'Binary File Detected'
                : isTooLarge
                ? 'File Too Large'
                : 'Unable to Read File'}
            </h4>
            <p style={styles.errorMessage}>{error}</p>
            <span style={styles.errorPathBadge}>Path: {filePath}</span>
          </div>
        </div>
      </div>
    );
  }

  // 4. File Content Display
  if (!contentResponse) {
    return null;
  }

  const lines = contentResponse.content.split('\n');

  return (
    <div style={styles.viewerContainer}>
      {/* File Metadata Header */}
      <div style={styles.viewerHeader}>
        <div style={styles.headerLeft}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <span style={styles.headerPath}>{contentResponse.path}</span>
        </div>

        <div style={styles.headerRight}>
          <span style={styles.metaBadge}>{lines.length} lines</span>
          <span style={styles.metaBadge}>{formatFileSize(contentResponse.size)}</span>
          <span style={styles.metaBadge}>{contentResponse.encoding.toUpperCase()}</span>
        </div>
      </div>

      {/* Code Viewer Body */}
      <div style={styles.codeContainer}>
        <div style={styles.lineNumbersColumn}>
          {lines.map((_, index) => (
            <span key={index + 1} style={styles.lineNumber}>
              {index + 1}
            </span>
          ))}
        </div>

        <pre style={styles.codePre}>
          <code>
            {lines.map((line, index) => (
              <div key={index} style={styles.codeLine}>
                {line || ' '}
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  viewerContainer: {
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    overflow: 'hidden',
    height: '100%',
    minHeight: '400px',
  },
  emptyContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    padding: '40px 20px',
    textAlign: 'center',
  },
  emptyIconCircle: {
    width: '48px',
    height: '48px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    color: 'var(--text-muted)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '14px',
  },
  emptyTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-main)',
    marginBottom: '6px',
  },
  emptySubtext: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    maxWidth: '320px',
    lineHeight: '1.4',
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    padding: '40px 20px',
    gap: '12px',
  },
  spinner: {
    width: '24px',
    height: '24px',
    border: '3px solid var(--border-default)',
    borderTopColor: 'var(--color-primary)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    fontSize: '13px',
    color: 'var(--text-muted)',
  },
  errorContainer: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '14px',
    padding: '24px',
    margin: '24px',
    backgroundColor: 'var(--color-error-bg)',
    border: '1px solid #FCA5A5',
    borderRadius: 'var(--radius-md)',
  },
  errorIconBox: {
    color: 'var(--color-error)',
    marginTop: '2px',
    flexShrink: 0,
  },
  errorContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  errorTitle: {
    fontSize: '15px',
    fontWeight: 700,
    color: 'var(--color-error)',
  },
  errorMessage: {
    fontSize: '13.5px',
    color: 'var(--text-main)',
    lineHeight: '1.4',
  },
  errorPathBadge: {
    fontSize: '11.5px',
    fontFamily: 'monospace',
    color: 'var(--text-muted)',
    marginTop: '4px',
  },
  viewerHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 16px',
    backgroundColor: 'var(--bg-surface)',
    borderBottom: '1px solid var(--border-default)',
    gap: '12px',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    minWidth: 0,
  },
  headerPath: {
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: 'monospace',
    color: 'var(--text-main)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexShrink: 0,
  },
  metaBadge: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-sm)',
  },
  codeContainer: {
    display: 'flex',
    overflow: 'auto',
    backgroundColor: 'var(--bg-app)',
    flex: 1,
    maxHeight: '520px',
  },
  lineNumbersColumn: {
    display: 'flex',
    flexDirection: 'column',
    padding: '12px 0',
    backgroundColor: 'var(--bg-surface)',
    borderRight: '1px solid var(--border-default)',
    userSelect: 'none',
    textAlign: 'right',
    minWidth: '44px',
    flexShrink: 0,
  },
  lineNumber: {
    fontSize: '12px',
    fontFamily: 'monospace',
    lineHeight: '20px',
    color: 'var(--text-subtle)',
    paddingRight: '10px',
  },
  codePre: {
    margin: 0,
    padding: '12px 16px',
    fontFamily: 'Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace',
    fontSize: '12.5px',
    lineHeight: '20px',
    color: 'var(--text-main)',
    overflowX: 'auto',
    flex: 1,
    whiteSpace: 'pre',
  },
  codeLine: {
    lineHeight: '20px',
  },
};

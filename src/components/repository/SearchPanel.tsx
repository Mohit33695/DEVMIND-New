import React, { useState } from 'react';
import { searchRepositoryCode } from '@/api/client';
import type { RepositorySearchResponse, SearchResultItem } from '@/types/repository';

interface SearchPanelProps {
  repoId?: string;
  onSelectFile: (path: string) => void;
}

export const SearchPanel: React.FC<SearchPanelProps> = ({
  repoId,
  onSelectFile,
}) => {
  const [query, setQuery] = useState<string>('');
  const [caseSensitive, setCaseSensitive] = useState<boolean>(false);
  const [fileExtension, setFileExtension] = useState<string>('');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchResult, setSearchResult] = useState<RepositorySearchResponse | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState<boolean>(false);

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    if (!repoId) {
      setSearchError('Repository ID is missing. Please select or re-upload a repository.');
      return;
    }

    setIsSearching(true);
    setSearchError(null);
    setHasSearched(true);

    try {
      const result = await searchRepositoryCode(repoId, trimmedQuery, {
        case_sensitive: caseSensitive,
        file_extension: fileExtension.trim() || undefined,
        max_results: 100,
      });
      setSearchResult(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Search failed due to a server error.';
      setSearchError(msg);
      setSearchResult(null);
    } finally {
      setIsSearching(false);
    }
  };

  const renderHighlightedLine = (item: SearchResultItem) => {
    const { line_content, match_start, match_end } = item;

    if (match_start < 0 || match_end > line_content.length || match_start >= match_end) {
      return <span>{line_content}</span>;
    }

    const before = line_content.slice(0, match_start);
    const match = line_content.slice(match_start, match_end);
    const after = line_content.slice(match_end);

    return (
      <span style={styles.snippetText}>
        {before}
        <mark style={styles.matchMark}>{match}</mark>
        {after}
      </span>
    );
  };

  return (
    <div style={styles.panelContainer}>
      {/* 1. Header Bar */}
      <div style={styles.panelHeader}>
        <div style={styles.headerLeft}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2.5">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <span style={styles.headerTitle}>Repository Code Search</span>
        </div>

        {searchResult && (
          <span style={styles.resultsBadge}>
            {searchResult.total_matches} {searchResult.total_matches === 1 ? 'match' : 'matches'} across {searchResult.total_files_searched} {searchResult.total_files_searched === 1 ? 'file' : 'files'}
          </span>
        )}
      </div>

      {/* 2. Search Controls Bar */}
      <form onSubmit={handleSearchSubmit} style={styles.searchForm}>
        <div style={styles.inputGroup}>
          <div style={styles.inputWrapper}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2" style={styles.inputIcon}>
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>

            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search code across repository files..."
              style={styles.searchInput}
            />
          </div>

          <button
            type="submit"
            disabled={isSearching || !query.trim()}
            style={{
              ...styles.searchBtn,
              ...(isSearching || !query.trim() ? styles.searchBtnDisabled : {}),
            }}
          >
            {isSearching ? (
              <>
                <span style={styles.spinnerDot} />
                Searching...
              </>
            ) : (
              'Search'
            )}
          </button>
        </div>

        {/* Filters Row */}
        <div style={styles.filtersRow}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={caseSensitive}
              onChange={(e) => setCaseSensitive(e.target.checked)}
              style={styles.checkboxInput}
            />
            <span>Case sensitive</span>
          </label>

          <div style={styles.extFilterGroup}>
            <span style={styles.extLabel}>File extension:</span>
            <input
              type="text"
              value={fileExtension}
              onChange={(e) => setFileExtension(e.target.value)}
              placeholder="e.g. .py, .ts"
              style={styles.extInput}
            />
          </div>
        </div>
      </form>

      {/* 3. Search States & Results Output */}
      {isSearching && (
        <div style={styles.statusBox}>
          <span style={styles.spinnerDotLarge} />
          <span>Searching codebase for <strong>"{query.trim()}"</strong>...</span>
        </div>
      )}

      {searchError && (
        <div role="alert" style={styles.errorBox}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <div style={styles.errorTextGroup}>
            <span style={styles.errorTitle}>Search Error</span>
            <span style={styles.errorMessage}>{searchError}</span>
          </div>
        </div>
      )}

      {!isSearching && !searchError && hasSearched && searchResult && searchResult.total_matches === 0 && (
        <div style={styles.emptyStateBox}>
          <div style={styles.emptyIconCircle}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h4 style={styles.emptyTitle}>No matches found for '{searchResult.query}'</h4>
          <p style={styles.emptySubtext}>
            Try disabling case sensitivity or clearing the file extension filter to broaden your code search.
          </p>
        </div>
      )}

      {!isSearching && !searchError && searchResult && searchResult.total_matches > 0 && (
        <div style={styles.resultsGrid}>
          {searchResult.matches.map((item, index) => (
            <div
              key={`${item.file_path}-${item.line_number}-${item.match_start}-${index}`}
              role="button"
              tabIndex={0}
              style={styles.resultCard}
              onClick={() => onSelectFile(item.file_path)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectFile(item.file_path);
                }
              }}
            >
              <div style={styles.resultHeader}>
                <span style={styles.filePathBadge}>{item.file_path}</span>
                <span style={styles.linePill}>Line {item.line_number}</span>
              </div>

              <div style={styles.snippetContainer}>
                <code>{renderHighlightedLine(item)}</code>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  panelContainer: {
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    marginBottom: '16px',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  panelHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 14px',
    backgroundColor: 'var(--bg-surface)',
    borderBottom: '1px solid var(--border-default)',
    gap: '12px',
    flexWrap: 'wrap',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  headerTitle: {
    fontSize: '12.5px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: 'var(--text-main)',
  },
  resultsBadge: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
  },
  searchForm: {
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    borderBottom: '1px solid var(--border-default)',
  },
  inputGroup: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  inputWrapper: {
    position: 'relative',
    flex: 1,
    minWidth: '240px',
    display: 'flex',
    alignItems: 'center',
  },
  inputIcon: {
    position: 'absolute',
    left: '10px',
    pointerEvents: 'none',
  },
  searchInput: {
    width: '100%',
    padding: '7px 12px 7px 32px',
    fontSize: '13px',
    color: 'var(--text-main)',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    outline: 'none',
  },
  searchBtn: {
    padding: '7px 16px',
    fontSize: '12.5px',
    fontWeight: 600,
    color: 'var(--text-on-primary)',
    backgroundColor: 'var(--color-primary)',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
  },
  searchBtnDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  spinnerDot: {
    width: '12px',
    height: '12px',
    border: '2px solid #FFFFFF',
    borderTopColor: 'transparent',
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'spin 0.8s linear infinite',
  },
  spinnerDotLarge: {
    width: '14px',
    height: '14px',
    border: '2px solid var(--border-default)',
    borderTopColor: 'var(--color-primary)',
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'spin 0.8s linear infinite',
  },
  filtersRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    flexWrap: 'wrap',
    fontSize: '12px',
    color: 'var(--text-muted)',
  },
  checkboxLabel: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    cursor: 'pointer',
    userSelect: 'none',
  },
  checkboxInput: {
    cursor: 'pointer',
  },
  extFilterGroup: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
  },
  extLabel: {
    color: 'var(--text-subtle)',
  },
  extInput: {
    padding: '3px 8px',
    fontSize: '11.5px',
    fontFamily: 'monospace',
    color: 'var(--text-main)',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    width: '90px',
    outline: 'none',
  },
  statusBox: {
    padding: '16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    fontSize: '13px',
    color: 'var(--text-muted)',
  },
  errorBox: {
    padding: '12px 16px',
    margin: '12px 14px',
    backgroundColor: 'var(--color-error-bg)',
    color: 'var(--color-error)',
    border: '1px solid #FCA5A5',
    borderRadius: 'var(--radius-sm)',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
  },
  errorTextGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  errorTitle: {
    fontSize: '12.5px',
    fontWeight: 700,
  },
  errorMessage: {
    fontSize: '12px',
    color: 'var(--text-main)',
  },
  emptyStateBox: {
    padding: '24px 16px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
  },
  emptyIconCircle: {
    width: '36px',
    height: '36px',
    borderRadius: '50%',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    color: 'var(--text-muted)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '8px',
  },
  emptyTitle: {
    fontSize: '13.5px',
    fontWeight: 600,
    color: 'var(--text-main)',
    marginBottom: '4px',
  },
  emptySubtext: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    maxWidth: '380px',
  },
  resultsGrid: {
    padding: '10px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    maxHeight: '260px',
    overflowY: 'auto',
  },
  resultCard: {
    padding: '8px 10px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    cursor: 'pointer',
    transition: 'border-color var(--transition-fast)',
  },
  resultHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '8px',
  },
  filePathBadge: {
    fontSize: '12px',
    fontWeight: 600,
    fontFamily: 'monospace',
    color: 'var(--color-primary)',
    wordBreak: 'break-word',
  },
  linePill: {
    fontSize: '11px',
    fontFamily: 'monospace',
    color: 'var(--text-subtle)',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    padding: '1px 6px',
    borderRadius: 'var(--radius-sm)',
    flexShrink: 0,
  },
  snippetContainer: {
    fontSize: '11.5px',
    fontFamily: 'monospace',
    backgroundColor: 'var(--bg-app)',
    padding: '4px 8px',
    borderRadius: 'var(--radius-sm)',
    overflowX: 'auto',
  },
  snippetText: {
    whiteSpace: 'pre',
    color: 'var(--text-muted)',
  },
  matchMark: {
    backgroundColor: '#FEF08A',
    color: '#854D0E',
    fontWeight: 700,
    padding: '0 2px',
    borderRadius: '2px',
  },
};

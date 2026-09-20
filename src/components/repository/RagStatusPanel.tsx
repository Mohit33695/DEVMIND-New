import React, { useState, useEffect } from 'react';
import {
  fetchRepositoryIndexStatus,
  indexRepositoryRAG,
  retrieveRepositoryRAG,
} from '@/api/client';
import type {
  RepositoryIndexStatus,
  RepositoryRetrievalResponse,
} from '@/types/repository';

interface RagStatusPanelProps {
  repoId?: string;
  onSelectFile?: (path: string) => void;
}

export const RagStatusPanel: React.FC<RagStatusPanelProps> = ({
  repoId,
  onSelectFile,
}) => {
  const [statusData, setStatusData] = useState<RepositoryIndexStatus | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState<boolean>(false);
  const [isIndexing, setIsIndexing] = useState<boolean>(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Retrieval query state
  const [query, setQuery] = useState<string>('');
  const [topK, setTopK] = useState<number>(5);
  const [retrievalData, setRetrievalData] = useState<RepositoryRetrievalResponse | null>(null);
  const [isRetrieving, setIsRetrieving] = useState<boolean>(false);
  const [retrievalError, setRetrievalError] = useState<string | null>(null);

  // Load status on mount or repo change
  useEffect(() => {
    if (!repoId) {
      setStatusData(null);
      setStatusError(null);
      setRetrievalData(null);
      return;
    }

    let isMounted = true;
    setIsLoadingStatus(true);
    setStatusError(null);

    fetchRepositoryIndexStatus(repoId)
      .then((res) => {
        if (isMounted) {
          setStatusData(res);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg =
            err instanceof Error ? err.message : 'Failed to fetch index status.';
          setStatusError(msg);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingStatus(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [repoId]);

  const handleIndexRepository = () => {
    if (!repoId) return;

    setIsIndexing(true);
    setStatusError(null);

    indexRepositoryRAG(repoId)
      .then((res) => {
        setStatusData(res);
      })
      .catch((err: unknown) => {
        const msg =
          err instanceof Error ? err.message : 'Failed to index repository.';
        setStatusError(msg);
      })
      .finally(() => {
        setIsIndexing(false);
      });
  };

  const handleExecuteRetrieval = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoId || !query.trim()) return;

    setIsRetrieving(true);
    setRetrievalError(null);

    retrieveRepositoryRAG(repoId, query.trim(), topK, 0.0)
      .then((res) => {
        setRetrievalData(res);
        // Refresh status to reflect indexed state
        fetchRepositoryIndexStatus(repoId).then(setStatusData).catch(() => {});
      })
      .catch((err: unknown) => {
        const msg =
          err instanceof Error ? err.message : 'Failed to execute retrieval.';
        setRetrievalError(msg);
      })
      .finally(() => {
        setIsRetrieving(false);
      });
  };

  // 1. Empty State (No Active Repo)
  if (!repoId) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.emptyPromptBox}>
          <div style={styles.emptyIconCircle}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
            </svg>
          </div>
          <h3 style={styles.emptyPromptTitle}>No Active Repository Selected</h3>
          <p style={styles.emptyPromptSubtext}>
            Upload a codebase archive on the Repository Scanner page to build semantic RAG vector indexes and perform code retrieval.
          </p>
        </div>
      </div>
    );
  }

  // 2. Loading Status State
  if (isLoadingStatus && !statusData) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.loadingBox}>
          <div style={styles.spinner} />
          <p style={styles.loadingText}>Reading RAG vector index status...</p>
        </div>
      </div>
    );
  }

  const isIndexed = statusData?.status === 'indexed';

  return (
    <div style={styles.panelContainer}>
      {/* Header */}
      <div style={styles.headerRow}>
        <div>
          <h2 style={styles.panelTitle}>RAG & Codebase Intelligence</h2>
          <p style={styles.panelSubtitle}>
            Hybrid symbol-aware vector indexing, mock embedding abstraction, and repository-scoped semantic retrieval
          </p>
        </div>
        <div style={styles.badgeGroup}>
          <span style={styles.providerNoticeBadge}>
            {statusData?.embedding_provider || 'MockEmbeddingProvider (Development/Test Mode)'}
          </span>
        </div>
      </div>

      {/* Mock Notice Banner */}
      <div style={styles.mockBanner}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px', flexShrink: 0 }}>
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span>
          <strong>Development/Test Mode Notice:</strong> Currently operating in local offline mock embedding mode (384-dim pseudo-vectors). Deterministic vectors are generated locally without external API keys or network dependencies.
        </span>
      </div>

      {/* Index Status KPI Cards */}
      <div style={styles.kpiGrid}>
        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Index Status</div>
          <div style={styles.kpiValueStatus}>
            <span
              style={
                statusData?.status === 'indexed'
                  ? styles.statusIndexed
                  : statusData?.status === 'indexing'
                  ? styles.statusIndexing
                  : statusData?.status === 'failed'
                  ? styles.statusFailed
                  : styles.statusNotIndexed
              }
            >
              {statusData?.status || 'not_indexed'}
            </span>
          </div>
          <div style={styles.kpiSubtext}>Repository RAG state</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Indexed Files</div>
          <div style={styles.kpiValue}>
            {statusData?.indexed_files || 0} / {statusData?.total_files || 0}
          </div>
          <div style={styles.kpiSubtext}>Allowlisted source files</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Total Chunks</div>
          <div style={styles.kpiValueHighlight}>{statusData?.total_chunks || 0}</div>
          <div style={styles.kpiSubtext}>Symbol-aware & line chunks</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Vector Dimension</div>
          <div style={styles.kpiValueSm}>{statusData?.embedding_dimension || 384}</div>
          <div style={styles.kpiSubtext}>Float vector array size</div>
        </div>
      </div>

      {/* Index Action Bar */}
      <div style={styles.actionRow}>
        <button
          style={isIndexing ? styles.btnDisabled : styles.btnPrimary}
          onClick={handleIndexRepository}
          disabled={isIndexing}
        >
          {isIndexing ? 'Indexing Repository...' : isIndexed ? 'Re-Index Repository' : 'Index Repository for RAG'}
        </button>

        {statusError && <span style={styles.errorInlineText}>{statusError}</span>}
      </div>

      {/* Semantic Retrieval Sandbox */}
      <div style={styles.sectionContainer}>
        <h3 style={styles.sectionTitle}>Semantic Retrieval Sandbox</h3>
        <p style={styles.sectionSubtext}>
          Test repository-isolated vector similarity search against indexed codebase chunks with source citations.
        </p>

        <form onSubmit={handleExecuteRetrieval} style={styles.searchForm}>
          <input
            type="text"
            placeholder="Enter natural language code query (e.g. 'How is path traversal prevented?')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={styles.searchInput}
          />
          <div style={styles.selectGroup}>
            <label style={styles.selectLabel}>Top K:</label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              style={styles.selectInput}
            >
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
            </select>
          </div>
          <button
            type="submit"
            style={isRetrieving ? styles.btnDisabled : styles.btnSecondary}
            disabled={isRetrieving || !query.trim()}
          >
            {isRetrieving ? 'Retrieving...' : 'Execute Vector Search'}
          </button>
        </form>

        {retrievalError && (
          <div style={styles.errorBoxInline}>
            <p style={styles.errorSubtext}>{retrievalError}</p>
          </div>
        )}

        {/* Retrieval Results List */}
        {retrievalData && (
          <div style={styles.resultsContainer}>
            <div style={styles.resultsHeader}>
              <span style={styles.resultsTitle}>
                Retrieved Chunks ({retrievalData.results.length} matches for &quot;{retrievalData.query}&quot;)
              </span>
            </div>

            {retrievalData.results.length === 0 ? (
              <div style={styles.emptyResultsBox}>
                <p style={styles.emptyStateSubtext}>
                  No code chunks matched similarity threshold for query &quot;{retrievalData.query}&quot;. Try indexing the repository first or broadening search query.
                </p>
              </div>
            ) : (
              <div style={styles.resultsList}>
                {retrievalData.results.map((res, i) => (
                  <div key={i} style={styles.resultCard}>
                    <div style={styles.resultCardHeader}>
                      <div style={styles.resultMetaLeft}>
                        <button
                          style={styles.fileLinkButton}
                          onClick={() => onSelectFile && onSelectFile(res.source_reference.file_path)}
                        >
                          {res.source_reference.file_path} (Lines {res.source_reference.start_line} - {res.source_reference.end_line})
                        </button>
                        {res.source_reference.symbol_name && (
                          <span style={styles.symbolTag}>
                            {res.chunk.symbol_kind || 'symbol'}: {res.source_reference.symbol_name}
                          </span>
                        )}
                      </div>

                      <span style={styles.scoreBadge}>
                        Similarity Score: {(res.relevance_score * 100).toFixed(1)}%
                      </span>
                    </div>

                    <pre style={styles.codeSnippetPre}>{res.chunk.content}</pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  panelContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
    padding: '24px',
    backgroundColor: '#0f172a',
    borderRadius: '12px',
    color: '#f8fafc',
    border: '1px solid #1e293b',
  },
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  panelTitle: {
    fontSize: '22px',
    fontWeight: '700',
    color: '#f8fafc',
    margin: 0,
  },
  panelSubtitle: {
    fontSize: '14px',
    color: '#94a3b8',
    marginTop: '4px',
    margin: 0,
  },
  badgeGroup: {
    display: 'flex',
    gap: '8px',
  },
  providerNoticeBadge: {
    padding: '4px 10px',
    backgroundColor: '#1e293b',
    color: '#a855f7',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '600',
    border: '1px solid #7e22ce',
  },
  mockBanner: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#3b0764',
    border: '1px solid #7e22ce',
    borderRadius: '8px',
    padding: '12px 16px',
    fontSize: '13px',
    color: '#e9d5ff',
  },
  kpiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '16px',
  },
  kpiCard: {
    backgroundColor: '#1e293b',
    borderRadius: '8px',
    padding: '16px',
    border: '1px solid #334155',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  kpiLabel: {
    fontSize: '12px',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    fontWeight: '600',
  },
  kpiValue: {
    fontSize: '24px',
    fontWeight: '800',
    color: '#38bdf8',
  },
  kpiValueStatus: {
    fontSize: '16px',
    fontWeight: '700',
    marginTop: '4px',
  },
  kpiValueSm: {
    fontSize: '22px',
    fontWeight: '700',
    color: '#a855f7',
  },
  kpiValueHighlight: {
    fontSize: '24px',
    fontWeight: '800',
    color: '#34d399',
  },
  kpiSubtext: {
    fontSize: '12px',
    color: '#64748b',
  },
  statusIndexed: {
    padding: '2px 8px',
    backgroundColor: '#064e3b',
    color: '#34d399',
    borderRadius: '4px',
    fontSize: '12px',
    textTransform: 'uppercase',
  },
  statusIndexing: {
    padding: '2px 8px',
    backgroundColor: '#075985',
    color: '#38bdf8',
    borderRadius: '4px',
    fontSize: '12px',
    textTransform: 'uppercase',
  },
  statusNotIndexed: {
    padding: '2px 8px',
    backgroundColor: '#334155',
    color: '#94a3b8',
    borderRadius: '4px',
    fontSize: '12px',
    textTransform: 'uppercase',
  },
  statusFailed: {
    padding: '2px 8px',
    backgroundColor: '#7f1d1d',
    color: '#fca5a5',
    borderRadius: '4px',
    fontSize: '12px',
    textTransform: 'uppercase',
  },
  actionRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  btnPrimary: {
    padding: '10px 20px',
    backgroundColor: '#0284c7',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  btnSecondary: {
    padding: '10px 20px',
    backgroundColor: '#7e22ce',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  btnDisabled: {
    padding: '10px 20px',
    backgroundColor: '#334155',
    color: '#94a3b8',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'not-allowed',
  },
  errorInlineText: {
    fontSize: '13px',
    color: '#fca5a5',
  },
  sectionContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    backgroundColor: '#1e293b',
    padding: '20px',
    borderRadius: '8px',
    border: '1px solid #334155',
  },
  sectionTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#f8fafc',
    margin: 0,
  },
  sectionSubtext: {
    fontSize: '13px',
    color: '#94a3b8',
    margin: 0,
  },
  searchForm: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginTop: '8px',
  },
  searchInput: {
    flex: 1,
    minWidth: '280px',
    padding: '10px 14px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#f8fafc',
    fontSize: '13px',
    outline: 'none',
  },
  selectGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  selectLabel: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  selectInput: {
    padding: '10px 8px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#f8fafc',
    fontSize: '13px',
  },
  resultsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    marginTop: '12px',
  },
  resultsHeader: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#cbd5e1',
  },
  resultsTitle: {
    color: '#38bdf8',
  },
  resultsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  resultCard: {
    backgroundColor: '#0f172a',
    borderRadius: '8px',
    padding: '14px',
    border: '1px solid #334155',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  resultCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '8px',
  },
  resultMetaLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  fileLinkButton: {
    background: 'none',
    border: 'none',
    color: '#38bdf8',
    cursor: 'pointer',
    padding: 0,
    fontFamily: 'monospace',
    fontSize: '13px',
    textDecoration: 'underline',
  },
  symbolTag: {
    padding: '2px 8px',
    backgroundColor: '#312e81',
    color: '#a5b4fc',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600',
  },
  scoreBadge: {
    padding: '2px 8px',
    backgroundColor: '#064e3b',
    color: '#34d399',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '700',
  },
  codeSnippetPre: {
    backgroundColor: '#020617',
    padding: '12px',
    borderRadius: '6px',
    color: '#e2e8f0',
    fontFamily: 'monospace',
    fontSize: '12px',
    overflowX: 'auto',
    margin: 0,
    whiteSpace: 'pre-wrap',
    maxHeight: '200px',
  },
  emptyResultsBox: {
    padding: '24px',
    textAlign: 'center',
    backgroundColor: '#0f172a',
    borderRadius: '8px',
  },
  emptyPromptBox: {
    padding: '48px 24px',
    textAlign: 'center',
    backgroundColor: '#1e293b',
    borderRadius: '8px',
    border: '1px solid #334155',
  },
  emptyIconCircle: {
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    backgroundColor: '#334155',
    color: '#38bdf8',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px auto',
  },
  emptyPromptTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#f8fafc',
    margin: '0 0 8px 0',
  },
  emptyPromptSubtext: {
    fontSize: '13px',
    color: '#94a3b8',
    maxWidth: '500px',
    margin: '0 auto',
  },
  emptyStateSubtext: {
    fontSize: '13px',
    color: '#94a3b8',
    margin: 0,
  },
  loadingBox: {
    padding: '48px',
    textAlign: 'center',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid #334155',
    borderTop: '3px solid #38bdf8',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 16px auto',
  },
  loadingText: {
    color: '#94a3b8',
    fontSize: '14px',
  },
  errorBoxInline: {
    padding: '12px',
    backgroundColor: '#7f1d1d',
    borderRadius: '6px',
    marginTop: '8px',
  },
  errorSubtext: {
    color: '#fecaca',
    fontSize: '13px',
    margin: 0,
  },
};

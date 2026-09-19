import React, { useState, useEffect, useMemo } from 'react';
import { fetchRepositoryDocumentation } from '@/api/client';
import type {
  RepositoryDocumentationResponse,
  SymbolItem,
} from '@/types/repository';

interface DocumentationPanelProps {
  repoId?: string;
  onSelectFile?: (path: string) => void;
}

type MainTab = 'overview' | 'api_symbols' | 'modules' | 'architecture';
type SymbolFilter = 'all' | 'function' | 'class' | 'method' | 'import';

export const DocumentationPanel: React.FC<DocumentationPanelProps> = ({
  repoId,
  onSelectFile,
}) => {
  const [data, setData] = useState<RepositoryDocumentationResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<MainTab>('overview');
  const [symbolFilter, setSymbolFilter] = useState<SymbolFilter>('all');
  const [moduleSearch, setModuleSearch] = useState<string>('');

  useEffect(() => {
    if (!repoId) {
      setData(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    fetchRepositoryDocumentation(repoId)
      .then((res) => {
        if (isMounted) {
          setData(res);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg =
            err instanceof Error
              ? err.message
              : 'Failed to fetch repository documentation.';
          setError(msg);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [repoId]);

  // Aggregate all symbols from modules
  const allSymbols = useMemo(() => {
    if (!data) return [];
    const list: SymbolItem[] = [];
    for (const mod of data.modules) {
      for (const sym of mod.symbols) {
        list.push(sym);
      }
    }
    return list;
  }, [data]);

  // Filtered symbols for Symbol Reference tab
  const filteredSymbols = useMemo(() => {
    if (symbolFilter === 'all') return allSymbols;
    return allSymbols.filter((s) => s.kind === symbolFilter);
  }, [allSymbols, symbolFilter]);

  // Filtered modules for Module Directory tab
  const filteredModules = useMemo(() => {
    if (!data) return [];
    if (!moduleSearch.trim()) return data.modules;
    const q = moduleSearch.toLowerCase();
    return data.modules.filter(
      (m) =>
        m.file_path.toLowerCase().includes(q) ||
        m.language.toLowerCase().includes(q) ||
        (m.summary_docstring && m.summary_docstring.toLowerCase().includes(q))
    );
  }, [data, moduleSearch]);

  // 1. Empty State (No Active Repo)
  if (!repoId) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.emptyPromptBox}>
          <div style={styles.emptyIconCircle}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <h3 style={styles.emptyPromptTitle}>No Active Repository Selected</h3>
          <p style={styles.emptyPromptSubtext}>
            Upload a codebase archive on the Repository Scanner page to auto-generate codebase documentation, module catalogs, and API references.
          </p>
        </div>
      </div>
    );
  }

  // 2. Loading State
  if (isLoading) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.loadingBox}>
          <div style={styles.spinner} />
          <span>Generating codebase documentation from AST symbols and repository structure...</span>
        </div>
      </div>
    );
  }

  // 3. Error State
  if (error) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.errorBox}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <div style={styles.errorTextGroup}>
            <span style={styles.errorTitle}>Documentation Generation Error</span>
            <span style={styles.errorMessage}>{error}</span>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div style={styles.panelContainer}>
      {/* Header Bar */}
      <div style={styles.panelHeader}>
        <div style={styles.headerTitleRow}>
          <div style={styles.headerLeft}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2.5">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <h2 style={styles.headerTitle}>Documentation Intelligence</h2>
          </div>
          <span style={styles.verifiedBadge}>Verified Static Analysis</span>
        </div>
        <p style={styles.headerSubtext}>
          Deterministic codebase knowledge base generated directly from repository file structure, AST code symbols, docstrings, and module import graphs.
        </p>
      </div>

      {/* Main Navigation Tabs */}
      <div style={styles.tabNav}>
        <button
          type="button"
          style={{ ...styles.navTabBtn, ...(activeTab === 'overview' ? styles.navTabActive : {}) }}
          onClick={() => setActiveTab('overview')}
        >
          Overview & README
        </button>

        <button
          type="button"
          style={{ ...styles.navTabBtn, ...(activeTab === 'api_symbols' ? styles.navTabActive : {}) }}
          onClick={() => setActiveTab('api_symbols')}
        >
          API & Symbol Reference ({allSymbols.length})
        </button>

        <button
          type="button"
          style={{ ...styles.navTabBtn, ...(activeTab === 'modules' ? styles.navTabActive : {}) }}
          onClick={() => setActiveTab('modules')}
        >
          Module Directory ({data.modules.length})
        </button>

        <button
          type="button"
          style={{ ...styles.navTabBtn, ...(activeTab === 'architecture' ? styles.navTabActive : {}) }}
          onClick={() => setActiveTab('architecture')}
        >
          Architecture & Dependencies
        </button>
      </div>

      {/* TAB 1: Overview & README */}
      {activeTab === 'overview' && (
        <div style={styles.tabSection}>
          {/* Summary Metric Cards */}
          <div style={styles.metricsGrid}>
            <div style={styles.metricCard}>
              <span style={styles.metricValue}>{data.overview.total_files}</span>
              <span style={styles.metricLabel}>Total Scanned Files</span>
            </div>

            <div style={styles.metricCard}>
              <span style={{ ...styles.metricValue, color: 'var(--color-primary)' }}>
                {data.overview.total_symbols}
              </span>
              <span style={styles.metricLabel}>Extracted AST Symbols</span>
            </div>

            <div style={styles.metricCard}>
              <span style={{ ...styles.metricValue, color: '#8B5CF6' }}>
                {Object.keys(data.overview.detected_languages).length}
              </span>
              <span style={styles.metricLabel}>Languages Detected</span>
            </div>

            <div style={styles.metricCard}>
              <span
                style={{
                  ...styles.metricValue,
                  color: data.overview.readme_file_path ? '#10B981' : 'var(--text-muted)',
                }}
              >
                {data.overview.readme_file_path ? 'Present' : 'None'}
              </span>
              <span style={styles.metricLabel}>Repository README</span>
            </div>
          </div>

          {/* Languages Breakdown Card */}
          <div style={styles.cardBox}>
            <h3 style={styles.cardTitle}>Detected Languages & Composition</h3>
            <div style={styles.langPillsList}>
              {Object.entries(data.overview.detected_languages).map(([lang, count]) => (
                <div key={lang} style={styles.langPill}>
                  <span style={styles.langName}>{lang}</span>
                  <span style={styles.langCount}>{count} {count === 1 ? 'file' : 'files'}</span>
                </div>
              ))}
            </div>
          </div>

          {/* README Content Section */}
          <div style={styles.cardBox}>
            <div style={styles.readmeHeader}>
              <h3 style={styles.cardTitle}>
                {data.overview.readme_file_path ? `Project README (${data.overview.readme_file_path})` : 'Repository Documentation'}
              </h3>
              {data.overview.readme_file_path && (
                <span
                  style={styles.filePathPill}
                  onClick={() => onSelectFile && onSelectFile(data.overview.readme_file_path!)}
                  title="Click to view file in Repository Explorer"
                >
                  View File
                </span>
              )}
            </div>

            {data.overview.readme_content ? (
              <pre style={styles.readmePre}>{data.overview.readme_content}</pre>
            ) : (
              <div style={styles.emptyCardBox}>
                <span>No README file (README.md, README.rst, README.txt) detected in the root of this repository.</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: API & Symbol Reference */}
      {activeTab === 'api_symbols' && (
        <div style={styles.tabSection}>
          {/* Symbol Kind Filter Bar */}
          <div style={styles.subFilterBar}>
            <button
              type="button"
              style={{ ...styles.filterBtn, ...(symbolFilter === 'all' ? styles.filterBtnActive : {}) }}
              onClick={() => setSymbolFilter('all')}
            >
              All ({allSymbols.length})
            </button>
            <button
              type="button"
              style={{ ...styles.filterBtn, ...(symbolFilter === 'function' ? styles.filterBtnActive : {}) }}
              onClick={() => setSymbolFilter('function')}
            >
              Functions
            </button>
            <button
              type="button"
              style={{ ...styles.filterBtn, ...(symbolFilter === 'class' ? styles.filterBtnActive : {}) }}
              onClick={() => setSymbolFilter('class')}
            >
              Classes
            </button>
            <button
              type="button"
              style={{ ...styles.filterBtn, ...(symbolFilter === 'method' ? styles.filterBtnActive : {}) }}
              onClick={() => setSymbolFilter('method')}
            >
              Methods
            </button>
            <button
              type="button"
              style={{ ...styles.filterBtn, ...(symbolFilter === 'import' ? styles.filterBtnActive : {}) }}
              onClick={() => setSymbolFilter('import')}
            >
              Imports
            </button>
          </div>

          {filteredSymbols.length === 0 ? (
            <div style={styles.emptyCardBox}>
              <span>No symbols found matching filter "{symbolFilter}".</span>
            </div>
          ) : (
            <div style={styles.symbolList}>
              {filteredSymbols.map((sym, idx) => (
                <div key={`${sym.file_path}-${sym.name}-${sym.line_start}-${idx}`} style={styles.symbolCard}>
                  <div style={styles.symbolCardHeader}>
                    <span style={getSymbolKindStyle(sym.kind)}>{sym.kind}</span>
                    <span style={styles.symbolName}>{sym.name}</span>

                    {sym.visibility && (
                      <span style={getVisibilityStyle(sym.visibility)}>{sym.visibility}</span>
                    )}

                    {sym.parent_symbol && (
                      <span style={styles.parentBadge}>Parent: {sym.parent_symbol}</span>
                    )}

                    <span
                      style={styles.symbolFilePath}
                      onClick={() => onSelectFile && onSelectFile(sym.file_path)}
                      title="Click to view file"
                    >
                      {sym.file_path}:{sym.line_start}
                    </span>
                  </div>

                  {sym.signature && (
                    <code style={styles.signatureCode}>{sym.signature}</code>
                  )}

                  {(sym.parameters && sym.parameters.length > 0 || sym.return_type) && (
                    <div style={styles.metaRow}>
                      {sym.parameters && sym.parameters.length > 0 && (
                        <span style={styles.metaBadge}>
                          Params: {sym.parameters.join(', ')}
                        </span>
                      )}
                      {sym.return_type && (
                        <span style={styles.metaBadge}>
                          Returns: {sym.return_type}
                        </span>
                      )}
                    </div>
                  )}

                  {sym.docstring && (
                    <p style={styles.docstringText}>{sym.docstring}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Module Directory */}
      {activeTab === 'modules' && (
        <div style={styles.tabSection}>
          {/* Module Search Input */}
          <div style={styles.searchBar}>
            <input
              type="text"
              placeholder="Search module by file path or language..."
              value={moduleSearch}
              onChange={(e) => setModuleSearch(e.target.value)}
              style={styles.searchInput}
            />
          </div>

          {filteredModules.length === 0 ? (
            <div style={styles.emptyCardBox}>
              <span>No modules match your search query.</span>
            </div>
          ) : (
            <div style={styles.modulesList}>
              {filteredModules.map((mod) => (
                <div key={mod.file_path} style={styles.moduleCard}>
                  <div style={styles.moduleHeader}>
                    <span
                      style={styles.filePathPill}
                      onClick={() => onSelectFile && onSelectFile(mod.file_path)}
                      title="Click to view file"
                    >
                      {mod.file_path}
                    </span>

                    <span style={styles.langPillBadge}>{mod.language}</span>

                    <div style={styles.moduleMetrics}>
                      <span style={styles.modMetricItem}>
                        Symbols: <strong>{mod.total_symbols}</strong>
                      </span>
                      <span style={styles.modMetricItem}>
                        Public: <strong style={{ color: 'var(--color-primary)' }}>{mod.public_symbols_count}</strong>
                      </span>
                      <span style={styles.modMetricItem}>
                        Imports: <strong>{mod.imports_count}</strong>
                      </span>
                      <span style={styles.modMetricItem}>
                        Imported By: <strong>{mod.imported_by_count}</strong>
                      </span>
                    </div>
                  </div>

                  {mod.summary_docstring && (
                    <p style={styles.moduleDocstring}>{mod.summary_docstring}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Architecture & Dependencies */}
      {activeTab === 'architecture' && (
        <div style={styles.tabSection}>
          <div style={styles.metricsGrid}>
            <div style={styles.metricCard}>
              <span style={{ ...styles.metricValue, color: 'var(--color-primary)' }}>
                {data.architecture.total_internal_dependencies}
              </span>
              <span style={styles.metricLabel}>Internal Module Linkages</span>
            </div>

            <div style={styles.metricCard}>
              <span style={{ ...styles.metricValue, color: '#8B5CF6' }}>
                {data.architecture.external_packages.length}
              </span>
              <span style={styles.metricLabel}>External Third-Party Packages</span>
            </div>

            <div style={styles.metricCard}>
              <span
                style={{
                  ...styles.metricValue,
                  color: data.architecture.has_circular_dependencies ? 'var(--color-error)' : 'var(--color-success)',
                }}
              >
                {data.architecture.has_circular_dependencies ? 'Detected' : 'Clean'}
              </span>
              <span style={styles.metricLabel}>Circular Dependencies</span>
            </div>
          </div>

          {/* External Packages Catalog */}
          <div style={styles.cardBox}>
            <h3 style={styles.cardTitle}>External Third-Party Package Dependencies</h3>
            {data.architecture.external_packages.length === 0 ? (
              <p style={styles.cardSubtext}>No external third-party package imports detected in this codebase.</p>
            ) : (
              <div style={styles.pkgPillsList}>
                {data.architecture.external_packages.map((pkg) => (
                  <span key={pkg} style={styles.pkgPill}>
                    {pkg}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Circular Dependencies Status */}
          {data.architecture.has_circular_dependencies && (
            <div style={styles.warningBox}>
              <div style={styles.warningHeader}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-error)" strokeWidth="2.5">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                <span style={styles.warningTitle}>
                  Circular Dependencies Warning ({data.architecture.circular_cycles_count} cycles)
                </span>
              </div>
              <p style={styles.warningSubtext}>
                Circular dependencies create tight coupling between modules. Review cycle details on the Architecture Intelligence view.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const getSymbolKindStyle = (kind: string): React.CSSProperties => {
  switch (kind) {
    case 'function':
    case 'async_function':
      return {
        fontSize: '10px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '1px 6px',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--color-primary)',
        backgroundColor: 'var(--color-primary-light)',
      };
    case 'class':
      return {
        fontSize: '10px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '1px 6px',
        borderRadius: 'var(--radius-sm)',
        color: '#8B5CF6',
        backgroundColor: '#F3E8FF',
      };
    case 'method':
      return {
        fontSize: '10px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '1px 6px',
        borderRadius: 'var(--radius-sm)',
        color: '#10B981',
        backgroundColor: '#ECFDF5',
      };
    default:
      return {
        fontSize: '10px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '1px 6px',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--text-muted)',
        backgroundColor: 'var(--bg-subtle)',
      };
  }
};

const getVisibilityStyle = (visibility: string): React.CSSProperties => {
  switch (visibility) {
    case 'public':
      return {
        fontSize: '10px',
        fontWeight: 600,
        padding: '1px 5px',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--color-success)',
        backgroundColor: 'var(--color-success-bg)',
      };
    case 'private':
      return {
        fontSize: '10px',
        fontWeight: 600,
        padding: '1px 5px',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--color-error)',
        backgroundColor: '#FEF2F2',
      };
    default:
      return {
        fontSize: '10px',
        fontWeight: 600,
        padding: '1px 5px',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--text-muted)',
        backgroundColor: 'var(--bg-subtle)',
      };
  }
};

const styles: Record<string, React.CSSProperties> = {
  panelContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    width: '100%',
  },
  emptyPromptBox: {
    padding: '48px 24px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
  },
  emptyIconCircle: {
    width: '52px',
    height: '52px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--color-primary-light)',
    color: 'var(--color-primary)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '16px',
  },
  emptyPromptTitle: {
    fontSize: '17px',
    fontWeight: 700,
    color: 'var(--text-main)',
    marginBottom: '6px',
  },
  emptyPromptSubtext: {
    fontSize: '13.5px',
    color: 'var(--text-muted)',
    maxWidth: '460px',
    lineHeight: '1.5',
  },
  loadingBox: {
    padding: '40px 24px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    fontSize: '13.5px',
    color: 'var(--text-muted)',
  },
  spinner: {
    width: '20px',
    height: '20px',
    border: '2.5px solid var(--border-default)',
    borderTopColor: 'var(--color-primary)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  errorBox: {
    padding: '16px 20px',
    backgroundColor: 'var(--color-error-bg)',
    color: 'var(--color-error)',
    border: '1px solid #FCA5A5',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
  },
  errorTextGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  errorTitle: {
    fontSize: '14px',
    fontWeight: 700,
  },
  errorMessage: {
    fontSize: '13px',
    color: 'var(--text-main)',
  },
  panelHeader: {
    padding: '16px 20px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
  },
  headerTitleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '4px',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  headerTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: 'var(--text-main)',
    margin: 0,
  },
  verifiedBadge: {
    fontSize: '11px',
    fontWeight: 700,
    color: '#059669',
    backgroundColor: '#D1FAE5',
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
  },
  headerSubtext: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    margin: 0,
    lineHeight: '1.4',
  },
  tabNav: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap',
    padding: '6px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
  },
  navTabBtn: {
    padding: '6px 14px',
    fontSize: '12.5px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  navTabActive: {
    color: 'var(--color-primary)',
    backgroundColor: 'var(--bg-app)',
    boxShadow: 'var(--shadow-sm)',
  },
  tabSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
    gap: '12px',
  },
  metricCard: {
    padding: '14px 16px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  metricValue: {
    fontSize: '22px',
    fontWeight: 700,
    color: 'var(--text-main)',
    lineHeight: '1.2',
  },
  metricLabel: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-muted)',
  },
  cardBox: {
    padding: '16px 20px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  cardTitle: {
    fontSize: '14px',
    fontWeight: 700,
    color: 'var(--text-main)',
    margin: 0,
  },
  cardSubtext: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    margin: 0,
  },
  langPillsList: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  langPill: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    fontSize: '12px',
  },
  langName: {
    fontWeight: 700,
    color: 'var(--text-main)',
  },
  langCount: {
    color: 'var(--text-muted)',
  },
  readmeHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  filePathPill: {
    fontSize: '12px',
    fontFamily: 'monospace',
    fontWeight: 600,
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    wordBreak: 'break-word',
  },
  readmePre: {
    margin: 0,
    padding: '16px',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    fontSize: '12.5px',
    fontFamily: 'monospace',
    lineHeight: '1.5',
    color: 'var(--text-main)',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    maxHeight: '500px',
    overflowY: 'auto',
  },
  emptyCardBox: {
    padding: '20px',
    textAlign: 'center',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--text-muted)',
    fontSize: '13px',
  },
  subFilterBar: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap',
  },
  filterBtn: {
    padding: '4px 10px',
    fontSize: '11.5px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  filterBtnActive: {
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    borderColor: 'var(--color-primary)',
  },
  symbolList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  symbolCard: {
    padding: '12px 16px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  symbolCardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  symbolName: {
    fontSize: '13.5px',
    fontFamily: 'monospace',
    fontWeight: 700,
    color: 'var(--text-main)',
  },
  parentBadge: {
    fontSize: '10.5px',
    color: 'var(--text-subtle)',
    backgroundColor: 'var(--bg-subtle)',
    padding: '1px 5px',
    borderRadius: 'var(--radius-sm)',
  },
  symbolFilePath: {
    fontSize: '11px',
    fontFamily: 'monospace',
    color: 'var(--text-muted)',
    marginLeft: 'auto',
    cursor: 'pointer',
  },
  signatureCode: {
    fontSize: '12px',
    fontFamily: 'monospace',
    color: 'var(--color-primary)',
    backgroundColor: 'var(--bg-app)',
    padding: '4px 8px',
    borderRadius: 'var(--radius-sm)',
    wordBreak: 'break-all',
  },
  metaRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  metaBadge: {
    fontSize: '11px',
    fontFamily: 'monospace',
    color: 'var(--text-muted)',
  },
  docstringText: {
    fontSize: '12.5px',
    color: 'var(--text-muted)',
    margin: 0,
    lineHeight: '1.4',
  },
  searchBar: {
    width: '100%',
  },
  searchInput: {
    width: '100%',
    padding: '8px 12px',
    fontSize: '13px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-surface)',
    color: 'var(--text-main)',
    outline: 'none',
  },
  modulesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  moduleCard: {
    padding: '14px 16px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  moduleHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap',
  },
  langPillBadge: {
    fontSize: '10.5px',
    fontWeight: 700,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-app)',
    padding: '1px 6px',
    borderRadius: 'var(--radius-sm)',
  },
  moduleMetrics: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginLeft: 'auto',
    fontSize: '11.5px',
  },
  modMetricItem: {
    color: 'var(--text-muted)',
  },
  moduleDocstring: {
    fontSize: '12.5px',
    color: 'var(--text-muted)',
    margin: 0,
    lineHeight: '1.4',
  },
  pkgPillsList: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  pkgPill: {
    fontSize: '12px',
    fontFamily: 'monospace',
    fontWeight: 600,
    color: '#8B5CF6',
    backgroundColor: '#F3E8FF',
    padding: '3px 9px',
    borderRadius: 'var(--radius-sm)',
  },
  warningBox: {
    padding: '14px 16px',
    backgroundColor: '#FEF2F2',
    border: '1px solid #FCA5A5',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  warningHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  warningTitle: {
    fontSize: '13.5px',
    fontWeight: 700,
    color: 'var(--color-error)',
  },
  warningSubtext: {
    fontSize: '12.5px',
    color: 'var(--text-main)',
    margin: 0,
  },
};

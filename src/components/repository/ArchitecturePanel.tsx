import React, { useState, useEffect, useMemo } from 'react';
import { fetchRepositoryDependencies } from '@/api/client';
import type {
  RepositoryDependenciesResponse,
} from '@/types/repository';

interface ArchitecturePanelProps {
  repoId?: string;
  onSelectFile?: (path: string) => void;
}

type FilterTab = 'all' | 'internal' | 'external' | 'unresolved' | 'circular';

export const ArchitecturePanel: React.FC<ArchitecturePanelProps> = ({
  repoId,
  onSelectFile,
}) => {
  const [data, setData] = useState<RepositoryDependenciesResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<FilterTab>('all');

  useEffect(() => {
    if (!repoId) {
      setData(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    fetchRepositoryDependencies(repoId)
      .then((res) => {
        if (isMounted) {
          setData(res);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to fetch repository dependencies.';
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

  // Set of file paths involved in circular dependency cycles
  const circularFilesSet = useMemo(() => {
    if (!data || !data.circular_dependency_cycles) return new Set<string>();
    const fileSet = new Set<string>();
    for (const cycle of data.circular_dependency_cycles) {
      for (const file of cycle) {
        fileSet.add(file);
      }
    }
    return fileSet;
  }, [data]);

  // Filtered dependencies list
  const filteredDependencies = useMemo(() => {
    if (!data) return [];
    if (activeTab === 'all') return data.dependencies;
    if (activeTab === 'internal') {
      return data.dependencies.filter(
        (d) => d.dependency_type === 'internal' && d.resolution_status === 'resolved'
      );
    }
    if (activeTab === 'external') {
      return data.dependencies.filter((d) => d.dependency_type === 'external');
    }
    if (activeTab === 'unresolved') {
      return data.dependencies.filter((d) => d.resolution_status === 'unresolved');
    }
    if (activeTab === 'circular') {
      return data.dependencies.filter(
        (d) =>
          circularFilesSet.has(d.source_file) &&
          d.target_file &&
          circularFilesSet.has(d.target_file)
      );
    }
    return data.dependencies;
  }, [data, activeTab, circularFilesSet]);

  const circularDependenciesCount = useMemo(() => {
    if (!data) return 0;
    return data.dependencies.filter(
      (d) =>
        circularFilesSet.has(d.source_file) &&
        d.target_file &&
        circularFilesSet.has(d.target_file)
    ).length;
  }, [data, circularFilesSet]);

  // 1. Empty State (No Active Repository)
  if (!repoId) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.emptyPromptBox}>
          <div style={styles.emptyIconCircle}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          </div>
          <h3 style={styles.emptyPromptTitle}>No Active Repository Selected</h3>
          <p style={styles.emptyPromptSubtext}>
            Upload a codebase archive on the Repository Scanner page to unlock Architecture Intelligence and dependency graph analysis.
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
          <span>Analyzing codebase architecture and dependency relationships...</span>
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
            <span style={styles.errorTitle}>Architecture Analysis Error</span>
            <span style={styles.errorMessage}>{error}</span>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div style={styles.panelContainer}>
      {/* 1. Header Bar */}
      <div style={styles.panelHeader}>
        <div>
          <div style={styles.headerTitleRow}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2.5">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
            <h2 style={styles.headerTitle}>Architecture Intelligence & Dependency Map</h2>
          </div>
          <p style={styles.headerSubtext}>
            Static import analysis mapping file relationships, internal module flows, external package boundaries, and circular cycles.
          </p>
        </div>
      </div>

      {/* 2. Metric Summary Cards */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <span style={styles.metricValue}>{data.total_dependencies}</span>
          <span style={styles.metricLabel}>Total Dependencies</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: 'var(--color-primary)' }}>
            {data.internal_dependencies_count}
          </span>
          <span style={styles.metricLabel}>Internal Resolved</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: '#8B5CF6' }}>
            {data.external_dependencies_count}
          </span>
          <span style={styles.metricLabel}>External & Stdlib</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: data.unresolved_dependencies_count > 0 ? '#D97706' : 'var(--text-muted)' }}>
            {data.unresolved_dependencies_count}
          </span>
          <span style={styles.metricLabel}>Unresolved / Unknown</span>
        </div>
      </div>

      {/* 3. Circular Dependency Warning Section */}
      {data.has_circular_dependencies && data.circular_dependency_cycles.length > 0 && (
        <div style={styles.circularWarningBox}>
          <div style={styles.warningHeader}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-error)" strokeWidth="2.5">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <span style={styles.warningTitle}>
              Circular Dependency Detected ({data.circular_dependency_cycles.length} {data.circular_dependency_cycles.length === 1 ? 'cycle' : 'cycles'})
            </span>
          </div>

          <div style={styles.cyclesList}>
            {data.circular_dependency_cycles.map((cycle, idx) => (
              <div key={idx} style={styles.cycleCard}>
                <span style={styles.cycleIndex}>Cycle #{idx + 1}:</span>
                <div style={styles.cycleBreadcrumb}>
                  {cycle.map((file, fIdx) => (
                    <React.Fragment key={fIdx}>
                      <span
                        style={styles.cycleFilePill}
                        onClick={() => onSelectFile && onSelectFile(file)}
                        title="Click to view file"
                      >
                        {file}
                      </span>
                      {fIdx < cycle.length - 1 && <span style={styles.cycleArrow}>➔</span>}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Filter Tabs Bar */}
      <div style={styles.filterBar}>
        <button
          type="button"
          style={{ ...styles.tabBtn, ...(activeTab === 'all' ? styles.tabBtnActive : {}) }}
          onClick={() => setActiveTab('all')}
        >
          All ({data.dependencies.length})
        </button>

        <button
          type="button"
          style={{ ...styles.tabBtn, ...(activeTab === 'internal' ? styles.tabBtnActive : {}) }}
          onClick={() => setActiveTab('internal')}
        >
          Internal ({data.internal_dependencies_count})
        </button>

        <button
          type="button"
          style={{ ...styles.tabBtn, ...(activeTab === 'external' ? styles.tabBtnActive : {}) }}
          onClick={() => setActiveTab('external')}
        >
          External ({data.external_dependencies_count})
        </button>

        <button
          type="button"
          style={{ ...styles.tabBtn, ...(activeTab === 'unresolved' ? styles.tabBtnActive : {}) }}
          onClick={() => setActiveTab('unresolved')}
        >
          Unresolved ({data.unresolved_dependencies_count})
        </button>

        {data.has_circular_dependencies && (
          <button
            type="button"
            style={{
              ...styles.tabBtn,
              ...(activeTab === 'circular' ? styles.tabBtnActive : {}),
              color: 'var(--color-error)',
            }}
            onClick={() => setActiveTab('circular')}
          >
            Circular ({circularDependenciesCount})
          </button>
        )}
      </div>

      {/* 5. Zero Dependencies State */}
      {data.dependencies.length === 0 && (
        <div style={styles.zeroStateBox}>
          <span>No import dependencies detected in this codebase.</span>
        </div>
      )}

      {/* 6. Empty Filter Result State */}
      {data.dependencies.length > 0 && filteredDependencies.length === 0 && (
        <div style={styles.zeroStateBox}>
          <span>No dependencies matching filter "{activeTab}".</span>
        </div>
      )}

      {/* 7. Dependency Relationship List */}
      {filteredDependencies.length > 0 && (
        <div style={styles.depsList}>
          {filteredDependencies.map((dep, idx) => {
            const isCircular =
              circularFilesSet.has(dep.source_file) &&
              Boolean(dep.target_file && circularFilesSet.has(dep.target_file));

            return (
              <div
                key={`${dep.source_file}-${dep.line_number}-${dep.module_name}-${idx}`}
                style={{
                  ...styles.depCard,
                  ...(isCircular ? styles.depCardCircular : {}),
                }}
              >
                <div style={styles.depCardHeader}>
                  {/* Source File */}
                  <span
                    style={styles.sourcePill}
                    onClick={() => onSelectFile && onSelectFile(dep.source_file)}
                    title="Source file (click to view)"
                  >
                    {dep.source_file}
                  </span>

                  {/* Directional Connector Arrow */}
                  <span style={styles.connectorArrow}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2.5">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </span>

                  {/* Target File or Module */}
                  {dep.target_file ? (
                    <span
                      style={styles.targetPill}
                      onClick={() => onSelectFile && onSelectFile(dep.target_file!)}
                      title="Target file (click to view)"
                    >
                      {dep.target_file}
                    </span>
                  ) : (
                    <span style={styles.externalModulePill}>
                      {dep.module_name}
                    </span>
                  )}

                  {/* Line Number */}
                  <span style={styles.lineBadge}>Line {dep.line_number}</span>
                </div>

                {/* Badges & Raw Import Row */}
                <div style={styles.depCardFooter}>
                  <span style={getKindBadgeStyle(dep.dependency_type)}>
                    {dep.dependency_type}
                  </span>

                  <span style={getStatusBadgeStyle(dep.resolution_status)}>
                    {dep.resolution_status}
                  </span>

                  {isCircular && (
                    <span style={styles.circularBadge}>
                      Circular Cycle
                    </span>
                  )}

                  <code style={styles.rawImportCode}>{dep.raw_import}</code>

                  {dep.imported_symbols && dep.imported_symbols.length > 0 && (
                    <span style={styles.symbolsHint}>
                      Symbols: {dep.imported_symbols.join(', ')}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const getKindBadgeStyle = (type: string): React.CSSProperties => {
  switch (type) {
    case 'internal':
      return {
        fontSize: '10px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '1px 6px',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--color-primary)',
        backgroundColor: 'var(--color-primary-light)',
      };
    case 'external':
      return {
        fontSize: '10px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '1px 6px',
        borderRadius: 'var(--radius-sm)',
        color: '#8B5CF6',
        backgroundColor: '#F3E8FF',
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

const getStatusBadgeStyle = (status: string): React.CSSProperties => {
  switch (status) {
    case 'resolved':
      return {
        fontSize: '10px',
        fontWeight: 600,
        padding: '1px 6px',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--color-success)',
        backgroundColor: 'var(--color-success-bg)',
      };
    case 'external':
      return {
        fontSize: '10px',
        fontWeight: 600,
        padding: '1px 6px',
        borderRadius: 'var(--radius-sm)',
        color: '#8B5CF6',
        backgroundColor: '#F3E8FF',
      };
    default:
      return {
        fontSize: '10px',
        fontWeight: 600,
        padding: '1px 6px',
        borderRadius: 'var(--radius-sm)',
        color: '#D97706',
        backgroundColor: '#FEF3C7',
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
    gap: '8px',
    marginBottom: '4px',
  },
  headerTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: 'var(--text-main)',
    margin: 0,
  },
  headerSubtext: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    margin: 0,
    lineHeight: '1.4',
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
  circularWarningBox: {
    padding: '16px 20px',
    backgroundColor: '#FEF2F2',
    border: '1px solid #FCA5A5',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  warningHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  warningTitle: {
    fontSize: '14px',
    fontWeight: 700,
    color: 'var(--color-error)',
  },
  cyclesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  cycleCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    flexWrap: 'wrap',
  },
  cycleIndex: {
    fontWeight: 700,
    color: 'var(--color-error)',
  },
  cycleBreadcrumb: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap',
  },
  cycleFilePill: {
    padding: '2px 8px',
    fontSize: '11.5px',
    fontFamily: 'monospace',
    fontWeight: 600,
    color: 'var(--color-error)',
    backgroundColor: '#FFFFFF',
    border: '1px solid #FCA5A5',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  cycleArrow: {
    color: 'var(--color-error)',
    fontWeight: 700,
  },
  filterBar: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap',
    padding: '8px 12px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
  },
  tabBtn: {
    padding: '4px 12px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    backgroundColor: 'transparent',
    border: '1px solid transparent',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  tabBtnActive: {
    color: 'var(--color-primary)',
    backgroundColor: 'var(--bg-app)',
    borderColor: 'var(--border-default)',
  },
  zeroStateBox: {
    padding: '24px',
    textAlign: 'center',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-muted)',
    fontSize: '13px',
  },
  depsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  depCard: {
    padding: '12px 16px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  depCardCircular: {
    borderColor: '#FCA5A5',
    backgroundColor: '#FFF5F5',
  },
  depCardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap',
  },
  sourcePill: {
    fontSize: '12.5px',
    fontFamily: 'monospace',
    fontWeight: 600,
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    wordBreak: 'break-word',
  },
  connectorArrow: {
    display: 'inline-flex',
    alignItems: 'center',
    color: 'var(--color-primary)',
  },
  targetPill: {
    fontSize: '12.5px',
    fontFamily: 'monospace',
    fontWeight: 600,
    color: '#10B981',
    backgroundColor: '#ECFDF5',
    padding: '2px 8px',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    wordBreak: 'break-word',
  },
  externalModulePill: {
    fontSize: '12.5px',
    fontFamily: 'monospace',
    fontWeight: 600,
    color: '#8B5CF6',
    backgroundColor: '#F3E8FF',
    padding: '2px 8px',
    borderRadius: 'var(--radius-sm)',
    wordBreak: 'break-word',
  },
  lineBadge: {
    fontSize: '11px',
    fontFamily: 'monospace',
    color: 'var(--text-subtle)',
    marginLeft: 'auto',
  },
  depCardFooter: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  circularBadge: {
    fontSize: '10px',
    fontWeight: 700,
    textTransform: 'uppercase',
    padding: '1px 6px',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--color-error)',
    backgroundColor: '#FEF2F2',
    border: '1px solid #FCA5A5',
  },
  rawImportCode: {
    fontSize: '11.5px',
    fontFamily: 'monospace',
    color: 'var(--text-muted)',
    marginLeft: '4px',
    wordBreak: 'break-all',
  },
  symbolsHint: {
    fontSize: '11px',
    color: 'var(--text-subtle)',
    marginLeft: 'auto',
  },
};

import React, { useState, useEffect, useMemo } from 'react';
import { fetchRepositoryQuality } from '@/api/client';
import type {
  RepositoryQualityResponse,
} from '@/types/repository';

interface QualityPanelProps {
  repoId?: string;
  onSelectFile?: (path: string) => void;
}

type SeverityFilter = 'ALL' | 'HIGH' | 'MEDIUM' | 'LOW';
type CategoryFilter = 'ALL' | 'complexity' | 'maintainability' | 'documentation' | 'architecture';

export const QualityPanel: React.FC<QualityPanelProps> = ({
  repoId,
  onSelectFile,
}) => {
  const [data, setData] = useState<RepositoryQualityResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('ALL');

  useEffect(() => {
    if (!repoId) {
      setData(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    fetchRepositoryQuality(repoId)
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
              : 'Failed to fetch repository quality analysis.';
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

  // Filtered findings list
  const filteredFindings = useMemo(() => {
    if (!data) return [];
    return data.findings.filter((f) => {
      const matchSeverity =
        severityFilter === 'ALL' || f.severity === severityFilter;
      const matchCategory =
        categoryFilter === 'ALL' || f.category === categoryFilter;
      return matchSeverity && matchCategory;
    });
  }, [data, severityFilter, categoryFilter]);

  // 1. Empty State (No Active Repo)
  if (!repoId) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.emptyPromptBox}>
          <div style={styles.emptyIconCircle}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <h3 style={styles.emptyPromptTitle}>No Active Repository Selected</h3>
          <p style={styles.emptyPromptSubtext}>
            Upload a codebase archive on the Repository Scanner page to evaluate code quality metrics, function spans, parameter thresholds, and architectural risks.
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
          <span>Evaluating codebase quality rules, AST symbol spans, and maintainability metrics...</span>
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
            <span style={styles.errorTitle}>Code Quality Analysis Error</span>
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
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <h2 style={styles.headerTitle}>Code Quality Intelligence</h2>
          </div>
          <span style={styles.verifiedBadge}>Verified Static Quality Engine</span>
        </div>
        <p style={styles.headerSubtext}>
          Deterministic static code quality evaluation auditing function spans, parameter thresholds, class sizes, documentation coverage, and architectural health.
        </p>
      </div>

      {/* Metric Scorecards */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <span style={styles.metricValue}>{data.summary.total_findings}</span>
          <span style={styles.metricLabel}>Total Quality Findings</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: 'var(--color-error)' }}>
            {data.summary.high_severity_count}
          </span>
          <span style={styles.metricLabel}>High Severity Findings</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: '#D97706' }}>
            {data.summary.medium_severity_count}
          </span>
          <span style={styles.metricLabel}>Medium Severity Findings</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: 'var(--color-primary)' }}>
            {data.summary.low_severity_count}
          </span>
          <span style={styles.metricLabel}>Low Severity Findings</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: '#10B981' }}>
            {data.summary.documentation_coverage_percentage}%
          </span>
          <span style={styles.metricLabel}>Documentation Coverage</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: '#8B5CF6' }}>
            {data.summary.average_function_length} lines
          </span>
          <span style={styles.metricLabel}>Avg Function Length</span>
        </div>
      </div>

      {/* Filter Control Bar */}
      <div style={styles.filterBar}>
        <div style={styles.filterGroup}>
          <span style={styles.filterGroupLabel}>Severity:</span>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(severityFilter === 'ALL' ? styles.filterBtnActive : {}) }}
            onClick={() => setSeverityFilter('ALL')}
          >
            All ({data.summary.total_findings})
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(severityFilter === 'HIGH' ? styles.filterBtnActive : {}) }}
            onClick={() => setSeverityFilter('HIGH')}
          >
            High ({data.summary.high_severity_count})
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(severityFilter === 'MEDIUM' ? styles.filterBtnActive : {}) }}
            onClick={() => setSeverityFilter('MEDIUM')}
          >
            Medium ({data.summary.medium_severity_count})
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(severityFilter === 'LOW' ? styles.filterBtnActive : {}) }}
            onClick={() => setSeverityFilter('LOW')}
          >
            Low ({data.summary.low_severity_count})
          </button>
        </div>

        <div style={styles.filterGroup}>
          <span style={styles.filterGroupLabel}>Category:</span>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(categoryFilter === 'ALL' ? styles.filterBtnActive : {}) }}
            onClick={() => setCategoryFilter('ALL')}
          >
            All
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(categoryFilter === 'complexity' ? styles.filterBtnActive : {}) }}
            onClick={() => setCategoryFilter('complexity')}
          >
            Complexity
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(categoryFilter === 'maintainability' ? styles.filterBtnActive : {}) }}
            onClick={() => setCategoryFilter('maintainability')}
          >
            Maintainability
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(categoryFilter === 'documentation' ? styles.filterBtnActive : {}) }}
            onClick={() => setCategoryFilter('documentation')}
          >
            Documentation
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(categoryFilter === 'architecture' ? styles.filterBtnActive : {}) }}
            onClick={() => setCategoryFilter('architecture')}
          >
            Architecture
          </button>
        </div>
      </div>

      {/* Quality Findings Section */}
      {data.findings.length === 0 ? (
        <div style={styles.successCardBox}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          <span style={styles.successTitle}>Clean Codebase Quality Audit</span>
          <p style={styles.successSubtext}>
            No quality rule violations or complexity warnings detected in this codebase archive.
          </p>
        </div>
      ) : filteredFindings.length === 0 ? (
        <div style={styles.emptyCardBox}>
          <span>No quality findings match the selected filters.</span>
        </div>
      ) : (
        <div style={styles.findingsList}>
          {filteredFindings.map((finding) => (
            <div key={finding.id} style={styles.findingCard}>
              <div style={styles.findingHeader}>
                <span style={getSeverityStyle(finding.severity)}>
                  {finding.severity}
                </span>

                <span style={styles.ruleBadge}>{finding.rule_name}</span>

                <span style={getTypeStyle(finding.finding_type)}>
                  {finding.finding_type === 'VERIFIED_FACT' ? 'Verified Fact' : 'Heuristic Risk'}
                </span>

                {finding.symbol_name && (
                  <span style={styles.symbolPill}>
                    {finding.symbol_name}
                  </span>
                )}

                <span
                  style={styles.filePathPill}
                  onClick={() => onSelectFile && onSelectFile(finding.file_path)}
                  title="Click to view file in Repository Explorer"
                >
                  {finding.file_path}
                  {finding.line_start ? `:${finding.line_start}` : ''}
                  {finding.line_end && finding.line_end !== finding.line_start ? `-${finding.line_end}` : ''}
                </span>
              </div>

              <p style={styles.findingMessage}>{finding.message}</p>

              {finding.metric_value !== undefined && finding.metric_value !== null && (
                <div style={styles.metricDetailRow}>
                  <span style={styles.metricDetailItem}>
                    Observed: <strong>{finding.metric_value}</strong>
                  </span>
                  {finding.threshold_value !== undefined && finding.threshold_value !== null && (
                    <span style={styles.metricDetailItem}>
                      Threshold: <strong>{finding.threshold_value}</strong>
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* File Health Overview Section */}
      <div style={styles.cardBox}>
        <div style={styles.fileHealthHeader}>
          <h3 style={styles.cardTitle}>File Health Overview</h3>
          <p style={styles.cardSubtext}>
            Codebase file health metrics, line counts, symbol density, and finding totals.
          </p>
        </div>

        <div style={styles.filesTable}>
          {data.files_summary.map((fileItem) => (
            <div key={fileItem.file_path} style={styles.fileTableRow}>
              <span
                style={styles.filePathPill}
                onClick={() => onSelectFile && onSelectFile(fileItem.file_path)}
                title="Click to view file"
              >
                {fileItem.file_path}
              </span>

              <span style={styles.langBadge}>{fileItem.language}</span>

              <div style={styles.fileStatsGroup}>
                <span style={styles.fileStatText}>
                  Lines: <strong>{fileItem.total_lines}</strong>
                </span>
                <span style={styles.fileStatText}>
                  Symbols: <strong>{fileItem.total_symbols}</strong>
                </span>
                <span
                  style={{
                    ...styles.fileStatText,
                    color: fileItem.findings_count > 0 ? '#D97706' : 'var(--text-muted)',
                  }}
                >
                  Findings: <strong>{fileItem.findings_count}</strong>
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const getSeverityStyle = (severity: string): React.CSSProperties => {
  switch (severity) {
    case 'HIGH':
      return {
        fontSize: '10.5px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '2px 7px',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--color-error)',
        backgroundColor: '#FEF2F2',
        border: '1px solid #FCA5A5',
      };
    case 'MEDIUM':
      return {
        fontSize: '10.5px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '2px 7px',
        borderRadius: 'var(--radius-sm)',
        color: '#D97706',
        backgroundColor: '#FEF3C7',
        border: '1px solid #FDE68A',
      };
    default:
      return {
        fontSize: '10.5px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '2px 7px',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--color-primary)',
        backgroundColor: 'var(--color-primary-light)',
        border: '1px solid var(--border-default)',
      };
  }
};

const getTypeStyle = (type: string): React.CSSProperties => {
  if (type === 'VERIFIED_FACT') {
    return {
      fontSize: '10px',
      fontWeight: 600,
      padding: '1px 6px',
      borderRadius: 'var(--radius-sm)',
      color: '#059669',
      backgroundColor: '#D1FAE5',
    };
  }
  return {
    fontSize: '10px',
    fontWeight: 600,
    padding: '1px 6px',
    borderRadius: 'var(--radius-sm)',
    color: '#8B5CF6',
    backgroundColor: '#F3E8FF',
  };
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
  filterBar: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    padding: '12px 16px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
  },
  filterGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap',
  },
  filterGroupLabel: {
    fontSize: '12px',
    fontWeight: 700,
    color: 'var(--text-main)',
    marginRight: '4px',
  },
  filterBtn: {
    padding: '3px 10px',
    fontSize: '11.5px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  filterBtnActive: {
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    borderColor: 'var(--color-primary)',
  },
  findingsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  findingCard: {
    padding: '12px 16px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  findingHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  ruleBadge: {
    fontSize: '12.5px',
    fontWeight: 700,
    color: 'var(--text-main)',
  },
  symbolPill: {
    fontSize: '11.5px',
    fontFamily: 'monospace',
    fontWeight: 600,
    color: 'var(--text-main)',
    backgroundColor: 'var(--bg-subtle)',
    padding: '1px 6px',
    borderRadius: 'var(--radius-sm)',
  },
  filePathPill: {
    fontSize: '11.5px',
    fontFamily: 'monospace',
    fontWeight: 600,
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    marginLeft: 'auto',
    wordBreak: 'break-word',
  },
  findingMessage: {
    fontSize: '13px',
    color: 'var(--text-main)',
    margin: 0,
    lineHeight: '1.4',
  },
  metricDetailRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    fontSize: '11.5px',
    color: 'var(--text-muted)',
  },
  metricDetailItem: {
    fontSize: '11.5px',
  },
  successCardBox: {
    padding: '32px 24px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
    gap: '8px',
  },
  successTitle: {
    fontSize: '15px',
    fontWeight: 700,
    color: '#10B981',
  },
  successSubtext: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    margin: 0,
  },
  emptyCardBox: {
    padding: '24px',
    textAlign: 'center',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-muted)',
    fontSize: '13px',
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
  fileHealthHeader: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  cardTitle: {
    fontSize: '15px',
    fontWeight: 700,
    color: 'var(--text-main)',
    margin: 0,
  },
  cardSubtext: {
    fontSize: '12.5px',
    color: 'var(--text-muted)',
    margin: 0,
  },
  filesTable: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  fileTableRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '8px 12px',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    flexWrap: 'wrap',
  },
  langBadge: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-surface)',
    padding: '1px 6px',
    borderRadius: 'var(--radius-sm)',
  },
  fileStatsGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginLeft: 'auto',
    fontSize: '12px',
  },
  fileStatText: {
    color: 'var(--text-muted)',
  },
};

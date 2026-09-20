import React, { useState, useEffect, useMemo } from 'react';
import { fetchRepositorySecurity } from '@/api/client';
import type {
  RepositorySecurityResponse,
} from '@/types/repository';

interface SecurityPanelProps {
  repoId?: string;
  onSelectFile?: (path: string) => void;
}

type SeverityFilter = 'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
type CategoryFilter = 'ALL' | 'secrets' | 'code_execution' | 'crypto' | 'web_security' | 'configuration';
type ClassificationFilter = 'ALL' | 'VERIFIED_STATIC_FINDING' | 'HEURISTIC_SECURITY_RISK';

export const SecurityPanel: React.FC<SecurityPanelProps> = ({
  repoId,
  onSelectFile,
}) => {
  const [data, setData] = useState<RepositorySecurityResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('ALL');
  const [classificationFilter, setClassificationFilter] = useState<ClassificationFilter>('ALL');

  useEffect(() => {
    if (!repoId) {
      setData(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    fetchRepositorySecurity(repoId)
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
              : 'Failed to fetch repository security analysis.';
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
      const matchClassification =
        classificationFilter === 'ALL' || f.classification === classificationFilter;
      return matchSeverity && matchCategory && matchClassification;
    });
  }, [data, severityFilter, categoryFilter, classificationFilter]);

  // 1. Empty State (No Active Repo)
  if (!repoId) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.emptyPromptBox}>
          <div style={styles.emptyIconCircle}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <h3 style={styles.emptyPromptTitle}>No Active Repository Selected</h3>
          <p style={styles.emptyPromptSubtext}>
            Upload a codebase archive on the Repository Scanner page to audit for hardcoded secrets, dangerous dynamic code execution, and configuration risks.
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
          <span>Auditing codebase for security patterns, secret signatures, and execution risks...</span>
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
            <span style={styles.errorTitle}>Security Analysis Error</span>
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
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <h2 style={styles.headerTitle}>Security Intelligence</h2>
          </div>
          <span style={styles.verifiedBadge}>Verified Static Security Engine</span>
        </div>
        <p style={styles.headerSubtext}>
          Static application security testing (SAST) auditing source code for hardcoded secrets, dangerous execution patterns, weak crypto, and insecure configuration.
        </p>
        <div style={styles.disclaimerBox}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#D97706" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>
            Static analysis identifies security-relevant patterns. Findings require developer review and do not automatically establish exploitability.
          </span>
        </div>
      </div>

      {/* Metric Scorecards */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <span style={styles.metricValue}>{data.summary.total_findings}</span>
          <span style={styles.metricLabel}>Total Security Findings</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: '#DC2626' }}>
            {data.summary.critical_severity_count}
          </span>
          <span style={styles.metricLabel}>Critical Severity</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: '#EA580C' }}>
            {data.summary.high_severity_count}
          </span>
          <span style={styles.metricLabel}>High Severity</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: '#D97706' }}>
            {data.summary.medium_severity_count}
          </span>
          <span style={styles.metricLabel}>Medium Severity</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: 'var(--color-primary)' }}>
            {data.summary.low_severity_count}
          </span>
          <span style={styles.metricLabel}>Low Severity</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: '#DC2626' }}>
            {data.summary.secrets_count}
          </span>
          <span style={styles.metricLabel}>Hardcoded Secrets</span>
        </div>

        <div style={styles.metricCard}>
          <span style={{ ...styles.metricValue, color: '#EA580C' }}>
            {data.summary.code_execution_count}
          </span>
          <span style={styles.metricLabel}>Unsafe Code Execution</span>
        </div>
      </div>

      {/* Multi-Axis Filter Bar */}
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
            style={{ ...styles.filterBtn, ...(severityFilter === 'CRITICAL' ? styles.filterBtnActive : {}) }}
            onClick={() => setSeverityFilter('CRITICAL')}
          >
            Critical ({data.summary.critical_severity_count})
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
            style={{ ...styles.filterBtn, ...(categoryFilter === 'secrets' ? styles.filterBtnActive : {}) }}
            onClick={() => setCategoryFilter('secrets')}
          >
            Secrets ({data.summary.secrets_count})
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(categoryFilter === 'code_execution' ? styles.filterBtnActive : {}) }}
            onClick={() => setCategoryFilter('code_execution')}
          >
            Code Execution ({data.summary.code_execution_count})
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(categoryFilter === 'crypto' ? styles.filterBtnActive : {}) }}
            onClick={() => setCategoryFilter('crypto')}
          >
            Crypto
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(categoryFilter === 'web_security' ? styles.filterBtnActive : {}) }}
            onClick={() => setCategoryFilter('web_security')}
          >
            Web Security ({data.summary.web_security_count})
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(categoryFilter === 'configuration' ? styles.filterBtnActive : {}) }}
            onClick={() => setCategoryFilter('configuration')}
          >
            Configuration
          </button>
        </div>

        <div style={styles.filterGroup}>
          <span style={styles.filterGroupLabel}>Classification:</span>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(classificationFilter === 'ALL' ? styles.filterBtnActive : {}) }}
            onClick={() => setClassificationFilter('ALL')}
          >
            All
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(classificationFilter === 'VERIFIED_STATIC_FINDING' ? styles.filterBtnActive : {}) }}
            onClick={() => setClassificationFilter('VERIFIED_STATIC_FINDING')}
          >
            Verified Static Findings
          </button>
          <button
            type="button"
            style={{ ...styles.filterBtn, ...(classificationFilter === 'HEURISTIC_SECURITY_RISK' ? styles.filterBtnActive : {}) }}
            onClick={() => setClassificationFilter('HEURISTIC_SECURITY_RISK')}
          >
            Heuristic Security Risks
          </button>
        </div>
      </div>

      {/* Findings List Section */}
      {data.findings.length === 0 ? (
        <div style={styles.successCardBox}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          <span style={styles.successTitle}>Clean Security Audit</span>
          <p style={styles.successSubtext}>
            Zero security-relevant patterns or hardcoded secrets detected in this codebase archive.
          </p>
        </div>
      ) : filteredFindings.length === 0 ? (
        <div style={styles.emptyCardBox}>
          <span>No security findings match the selected filters.</span>
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

                <span style={getTypeStyle(finding.classification)}>
                  {finding.classification === 'VERIFIED_STATIC_FINDING' ? 'Verified Finding' : 'Heuristic Risk'}
                </span>

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

              {finding.evidence && (
                <div style={styles.evidenceBox}>
                  <span style={styles.evidenceLabel}>Evidence:</span>
                  <code style={styles.evidenceCode}>{finding.evidence}</code>
                </div>
              )}

              {finding.remediation && (
                <div style={styles.remediationBox}>
                  <strong style={styles.remediationLabel}>Remediation:</strong>
                  <span style={styles.remediationText}>{finding.remediation}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const getSeverityStyle = (severity: string): React.CSSProperties => {
  switch (severity) {
    case 'CRITICAL':
      return {
        fontSize: '10.5px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '2px 7px',
        borderRadius: 'var(--radius-sm)',
        color: '#DC2626',
        backgroundColor: '#FEF2F2',
        border: '1px solid #FCA5A5',
      };
    case 'HIGH':
      return {
        fontSize: '10.5px',
        fontWeight: 700,
        textTransform: 'uppercase',
        padding: '2px 7px',
        borderRadius: 'var(--radius-sm)',
        color: '#EA580C',
        backgroundColor: '#FFEDD5',
        border: '1px solid #FDBA74',
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

const getTypeStyle = (classification: string): React.CSSProperties => {
  if (classification === 'VERIFIED_STATIC_FINDING') {
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
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  headerTitleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
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
  disclaimerBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    backgroundColor: '#FEF3C7',
    border: '1px solid #FDE68A',
    borderRadius: 'var(--radius-sm)',
    fontSize: '12px',
    color: '#92400E',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
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
    gap: '8px',
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
  evidenceBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '11.5px',
    backgroundColor: 'var(--bg-app)',
    padding: '6px 10px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-default)',
  },
  evidenceLabel: {
    fontWeight: 700,
    color: 'var(--text-muted)',
  },
  evidenceCode: {
    fontFamily: 'monospace',
    color: 'var(--text-main)',
    wordBreak: 'break-all',
  },
  remediationBox: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    lineHeight: '1.4',
  },
  remediationLabel: {
    color: 'var(--text-main)',
    marginRight: '4px',
  },
  remediationText: {
    color: 'var(--text-muted)',
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
};

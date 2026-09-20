import React, { useState, useEffect, useMemo } from 'react';
import { fetchRepositoryTesting } from '@/api/client';
import type {
  RepositoryTestingResponse,
} from '@/types/repository';

interface TestingPanelProps {
  repoId?: string;
  onSelectFile?: (path: string) => void;
}

type TabType = 'inventory' | 'coverage' | 'findings';
type SeverityFilter = 'ALL' | 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH';
type CategoryFilter = 'ALL' | 'inventory' | 'framework' | 'quality' | 'coverage_gap';

export const TestingPanel: React.FC<TestingPanelProps> = ({
  repoId,
  onSelectFile,
}) => {
  const [data, setData] = useState<RepositoryTestingResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<TabType>('inventory');
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    if (!repoId) {
      setData(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    fetchRepositoryTesting(repoId)
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
              : 'Failed to fetch repository testing analysis.';
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
      const matchQuery =
        !searchQuery ||
        f.file_path.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.rule_id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchSeverity && matchCategory && matchQuery;
    });
  }, [data, severityFilter, categoryFilter, searchQuery]);

  // Filtered source mappings
  const filteredMappings = useMemo(() => {
    if (!data) return [];
    if (!searchQuery) return data.source_mappings;
    const q = searchQuery.toLowerCase();
    return data.source_mappings.filter(
      (m) =>
        m.source_file.toLowerCase().includes(q) ||
        (m.matching_test_file && m.matching_test_file.toLowerCase().includes(q))
    );
  }, [data, searchQuery]);

  // Filtered test files
  const filteredTestFiles = useMemo(() => {
    if (!data) return [];
    if (!searchQuery) return data.test_files;
    const q = searchQuery.toLowerCase();
    return data.test_files.filter((t) => t.file_path.toLowerCase().includes(q));
  }, [data, searchQuery]);

  // 1. Empty State (No Active Repo)
  if (!repoId) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.emptyPromptBox}>
          <div style={styles.emptyIconCircle}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
            </svg>
          </div>
          <h3 style={styles.emptyPromptTitle}>No Active Repository Selected</h3>
          <p style={styles.emptyPromptSubtext}>
            Upload a codebase archive on the Repository Scanner page to inspect static test suites, frameworks, and coverage heuristics.
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
          <p style={styles.loadingText}>Performing static testing intelligence analysis...</p>
        </div>
      </div>
    );
  }

  // 3. Error State
  if (error || !data) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.errorBox}>
          <h4 style={styles.errorTitle}>Testing Intelligence Error</h4>
          <p style={styles.errorSubtext}>{error || 'Unable to load testing analysis.'}</p>
        </div>
      </div>
    );
  }

  const { metrics, test_files, findings } = data;

  return (
    <div style={styles.panelContainer}>
      {/* Header */}
      <div style={styles.headerRow}>
        <div>
          <h2 style={styles.panelTitle}>Testing Intelligence</h2>
          <p style={styles.panelSubtitle}>
            Static test suite inventory, assertion counts, framework detection, and source-to-test mapping heuristics
          </p>
        </div>
        <div style={styles.badgeGroup}>
          <span style={styles.staticNoticeBadge}>Deterministic Static Analysis</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={styles.kpiGrid}>
        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Test Files</div>
          <div style={styles.kpiValue}>{metrics.total_test_files}</div>
          <div style={styles.kpiSubtext}>Identified test suites</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Test Functions</div>
          <div style={styles.kpiValue}>{metrics.total_test_functions}</div>
          <div style={styles.kpiSubtext}>Static test declarations</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Assertions Found</div>
          <div style={styles.kpiValue}>{metrics.total_assertions_detected}</div>
          <div style={styles.kpiSubtext}>Validation assert statements</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Frameworks</div>
          <div style={styles.kpiValueSm}>
            {metrics.detected_frameworks.length > 0
              ? metrics.detected_frameworks.join(', ')
              : 'Unknown'}
          </div>
          <div style={styles.kpiSubtext}>Static import footprints</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Static Test Ratio</div>
          <div style={styles.kpiValueHighlight}>{metrics.estimated_test_ratio}%</div>
          <div style={styles.kpiSubtext}>Files with obvious test suites</div>
        </div>
      </div>

      {/* Warning Notice */}
      <div style={styles.disclaimerBanner}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px', flexShrink: 0 }}>
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span>
          <strong>Static Signal Notice:</strong> Static Test Ratio measures files with matching test conventions and does not represent dynamic runtime branch or line coverage. Repository code is never executed.
        </span>
      </div>

      {/* Controls & Search */}
      <div style={styles.controlsRow}>
        <div style={styles.tabsContainer}>
          <button
            style={activeTab === 'inventory' ? styles.tabActive : styles.tabInactive}
            onClick={() => setActiveTab('inventory')}
          >
            Test Inventory ({test_files.length})
          </button>
          <button
            style={activeTab === 'coverage' ? styles.tabActive : styles.tabInactive}
            onClick={() => setActiveTab('coverage')}
          >
            Source Mappings ({data.source_mappings.length})
          </button>
          <button
            style={activeTab === 'findings' ? styles.tabActive : styles.tabInactive}
            onClick={() => setActiveTab('findings')}
          >
            Quality Signals ({findings.length})
          </button>
        </div>

        <div style={styles.searchBox}>
          <input
            type="text"
            placeholder="Search files or signals..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={styles.searchInput}
          />
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'inventory' && (
        <div style={styles.sectionContainer}>
          {filteredTestFiles.length === 0 ? (
            <div style={styles.emptyStateContainer}>
              <h4 style={styles.emptyStateTitle}>No Test Files Detected</h4>
              <p style={styles.emptyStateSubtext}>
                No test files were recognized using standard naming conventions (e.g., test_*.py, *.test.ts, *Test.java, *_test.go).
              </p>
            </div>
          ) : (
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Test File Path</th>
                    <th style={styles.th}>Language</th>
                    <th style={styles.th}>Framework</th>
                    <th style={styles.th}>Test Functions</th>
                    <th style={styles.th}>Assertions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTestFiles.map((tf, i) => (
                    <tr key={i} style={styles.tr}>
                      <td style={styles.td}>
                        <button
                          style={styles.fileLinkButton}
                          onClick={() => onSelectFile && onSelectFile(tf.file_path)}
                        >
                          {tf.file_path}
                        </button>
                      </td>
                      <td style={styles.td}>
                        <span style={styles.langBadge}>{tf.language}</span>
                      </td>
                      <td style={styles.td}>
                        <span style={styles.frameworkBadge}>{tf.framework}</span>
                      </td>
                      <td style={styles.tdNum}>{tf.test_function_count}</td>
                      <td style={styles.tdNum}>{tf.assertion_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'coverage' && (
        <div style={styles.sectionContainer}>
          {filteredMappings.length === 0 ? (
            <div style={styles.emptyStateContainer}>
              <p style={styles.emptyStateSubtext}>No source file mappings match query.</p>
            </div>
          ) : (
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Source File</th>
                    <th style={styles.th}>Matching Test Suite</th>
                    <th style={styles.th}>Confidence Signal</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMappings.map((m, i) => (
                    <tr key={i} style={styles.tr}>
                      <td style={styles.td}>
                        <button
                          style={styles.fileLinkButton}
                          onClick={() => onSelectFile && onSelectFile(m.source_file)}
                        >
                          {m.source_file}
                        </button>
                      </td>
                      <td style={styles.td}>
                        {m.matching_test_file ? (
                          <button
                            style={styles.fileLinkButtonSuccess}
                            onClick={() => onSelectFile && onSelectFile(m.matching_test_file!)}
                          >
                            {m.matching_test_file}
                          </button>
                        ) : (
                          <span style={styles.noTestTag}>No Obvious Matching Test</span>
                        )}
                      </td>
                      <td style={styles.td}>
                        <span
                          style={
                            m.confidence === 'HIGH'
                              ? styles.confidenceHigh
                              : m.confidence === 'MEDIUM'
                              ? styles.confidenceMedium
                              : styles.confidenceNone
                          }
                        >
                          {m.confidence}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'findings' && (
        <div style={styles.sectionContainer}>
          {/* Sub Filters */}
          <div style={styles.filtersSubRow}>
            <div style={styles.filterGroup}>
              <span style={styles.filterLabel}>Severity:</span>
              {(['ALL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as SeverityFilter[]).map((sev) => (
                <button
                  key={sev}
                  style={severityFilter === sev ? styles.filterChipActive : styles.filterChip}
                  onClick={() => setSeverityFilter(sev)}
                >
                  {sev}
                </button>
              ))}
            </div>

            <div style={styles.filterGroup}>
              <span style={styles.filterLabel}>Category:</span>
              {(['ALL', 'inventory', 'framework', 'quality', 'coverage_gap'] as CategoryFilter[]).map((cat) => (
                <button
                  key={cat}
                  style={categoryFilter === cat ? styles.filterChipActive : styles.filterChip}
                  onClick={() => setCategoryFilter(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {filteredFindings.length === 0 ? (
            <div style={styles.emptyStateContainer}>
              <p style={styles.emptyStateSubtext}>No quality signals match current filters.</p>
            </div>
          ) : (
            <div style={styles.findingsList}>
              {filteredFindings.map((item) => (
                <div key={item.id} style={styles.findingCard}>
                  <div style={styles.findingHeader}>
                    <div style={styles.findingTitleGroup}>
                      <span
                        style={
                          item.severity === 'HIGH'
                            ? styles.badgeHigh
                            : item.severity === 'MEDIUM'
                            ? styles.badgeMedium
                            : item.severity === 'LOW'
                            ? styles.badgeLow
                            : styles.badgeInfo
                        }
                      >
                        {item.severity}
                      </span>
                      <span style={styles.categoryBadge}>{item.category}</span>
                      <span style={styles.ruleIdText}>{item.rule_name} ({item.rule_id})</span>
                    </div>

                    <span style={styles.classificationTag}>{item.classification}</span>
                  </div>

                  <p style={styles.findingMessage}>{item.message}</p>

                  <div style={styles.findingLocationRow}>
                    <span style={styles.locationLabel}>File:</span>
                    <button
                      style={styles.locationButton}
                      onClick={() => onSelectFile && onSelectFile(item.file_path)}
                    >
                      {item.file_path} {item.line_start ? `(Line ${item.line_start})` : ''}
                    </button>
                  </div>

                  {item.evidence && (
                    <div style={styles.evidenceBox}>
                      <span style={styles.evidenceLabel}>Evidence:</span> {item.evidence}
                    </div>
                  )}

                  {item.remediation && (
                    <div style={styles.remediationBox}>
                      <span style={styles.remediationLabel}>Remediation:</span> {item.remediation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
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
  staticNoticeBadge: {
    padding: '4px 10px',
    backgroundColor: '#1e293b',
    color: '#38bdf8',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '600',
    border: '1px solid #0284c7',
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
    fontSize: '28px',
    fontWeight: '800',
    color: '#38bdf8',
  },
  kpiValueSm: {
    fontSize: '20px',
    fontWeight: '700',
    color: '#a855f7',
    wordBreak: 'break-word',
  },
  kpiValueHighlight: {
    fontSize: '28px',
    fontWeight: '800',
    color: '#34d399',
  },
  kpiSubtext: {
    fontSize: '12px',
    color: '#64748b',
  },
  disclaimerBanner: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#1e1b4b',
    border: '1px solid #4338ca',
    borderRadius: '8px',
    padding: '12px 16px',
    fontSize: '13px',
    color: '#c7d2fe',
  },
  controlsRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '12px',
  },
  tabsContainer: {
    display: 'flex',
    gap: '8px',
    backgroundColor: '#1e293b',
    padding: '4px',
    borderRadius: '8px',
  },
  tabActive: {
    padding: '8px 16px',
    backgroundColor: '#0284c7',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  tabInactive: {
    padding: '8px 16px',
    backgroundColor: 'transparent',
    color: '#94a3b8',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  searchBox: {
    minWidth: '240px',
  },
  searchInput: {
    width: '100%',
    padding: '8px 12px',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#f8fafc',
    fontSize: '13px',
    outline: 'none',
  },
  sectionContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  tableWrapper: {
    overflowX: 'auto',
    borderRadius: '8px',
    border: '1px solid #334155',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
    fontSize: '13px',
  },
  th: {
    backgroundColor: '#1e293b',
    color: '#94a3b8',
    padding: '12px 16px',
    fontWeight: '600',
    borderBottom: '1px solid #334155',
  },
  tr: {
    borderBottom: '1px solid #1e293b',
  },
  td: {
    padding: '12px 16px',
    color: '#e2e8f0',
  },
  tdNum: {
    padding: '12px 16px',
    color: '#38bdf8',
    fontWeight: '600',
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
  fileLinkButtonSuccess: {
    background: 'none',
    border: 'none',
    color: '#34d399',
    cursor: 'pointer',
    padding: 0,
    fontFamily: 'monospace',
    fontSize: '13px',
    textDecoration: 'underline',
  },
  langBadge: {
    padding: '2px 8px',
    backgroundColor: '#334155',
    color: '#f1f5f9',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600',
  },
  frameworkBadge: {
    padding: '2px 8px',
    backgroundColor: '#312e81',
    color: '#a5b4fc',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600',
  },
  noTestTag: {
    color: '#64748b',
    fontStyle: 'italic',
    fontSize: '12px',
  },
  confidenceHigh: {
    padding: '2px 8px',
    backgroundColor: '#065f46',
    color: '#34d399',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '700',
  },
  confidenceMedium: {
    padding: '2px 8px',
    backgroundColor: '#854d0e',
    color: '#fde047',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '700',
  },
  confidenceNone: {
    padding: '2px 8px',
    backgroundColor: '#334155',
    color: '#94a3b8',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600',
  },
  filtersSubRow: {
    display: 'flex',
    gap: '20px',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  filterGroup: {
    display: 'flex',
    gap: '6px',
    alignItems: 'center',
  },
  filterLabel: {
    fontSize: '12px',
    color: '#64748b',
    marginRight: '4px',
  },
  filterChip: {
    padding: '4px 10px',
    backgroundColor: '#1e293b',
    color: '#94a3b8',
    border: '1px solid #334155',
    borderRadius: '16px',
    fontSize: '11px',
    cursor: 'pointer',
  },
  filterChipActive: {
    padding: '4px 10px',
    backgroundColor: '#0284c7',
    color: '#ffffff',
    border: '1px solid #0284c7',
    borderRadius: '16px',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  findingsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  findingCard: {
    backgroundColor: '#1e293b',
    borderRadius: '8px',
    padding: '16px',
    border: '1px solid #334155',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  findingHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '8px',
  },
  findingTitleGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  badgeHigh: {
    padding: '2px 8px',
    backgroundColor: '#7f1d1d',
    color: '#fca5a5',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '700',
  },
  badgeMedium: {
    padding: '2px 8px',
    backgroundColor: '#78350f',
    color: '#fde047',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '700',
  },
  badgeLow: {
    padding: '2px 8px',
    backgroundColor: '#14532d',
    color: '#86efac',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '700',
  },
  badgeInfo: {
    padding: '2px 8px',
    backgroundColor: '#0c4a6e',
    color: '#7dd3fc',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '700',
  },
  categoryBadge: {
    padding: '2px 8px',
    backgroundColor: '#334155',
    color: '#cbd5e1',
    borderRadius: '4px',
    fontSize: '11px',
  },
  ruleIdText: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#f8fafc',
  },
  classificationTag: {
    fontSize: '11px',
    color: '#64748b',
    fontStyle: 'italic',
  },
  findingMessage: {
    fontSize: '13px',
    color: '#cbd5e1',
    margin: 0,
  },
  findingLocationRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
  },
  locationLabel: {
    color: '#64748b',
  },
  locationButton: {
    background: 'none',
    border: 'none',
    color: '#38bdf8',
    cursor: 'pointer',
    padding: 0,
    fontFamily: 'monospace',
    fontSize: '12px',
    textDecoration: 'underline',
  },
  evidenceBox: {
    backgroundColor: '#0f172a',
    padding: '8px 12px',
    borderRadius: '4px',
    fontSize: '12px',
    color: '#94a3b8',
    fontFamily: 'monospace',
  },
  evidenceLabel: {
    color: '#f59e0b',
    fontWeight: '600',
  },
  remediationBox: {
    backgroundColor: '#064e3b',
    color: '#a7f3d0',
    padding: '8px 12px',
    borderRadius: '4px',
    fontSize: '12px',
  },
  remediationLabel: {
    fontWeight: '700',
  },
  emptyStateContainer: {
    padding: '40px 20px',
    textAlign: 'center',
    backgroundColor: '#1e293b',
    borderRadius: '8px',
    border: '1px solid #334155',
  },
  emptyStateTitle: {
    fontSize: '16px',
    color: '#f8fafc',
    margin: '0 0 8px 0',
  },
  emptyStateSubtext: {
    fontSize: '13px',
    color: '#94a3b8',
    margin: 0,
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
  errorBox: {
    padding: '24px',
    backgroundColor: '#7f1d1d',
    border: '1px solid #ef4444',
    borderRadius: '8px',
  },
  errorTitle: {
    color: '#fca5a5',
    margin: '0 0 8px 0',
  },
  errorSubtext: {
    color: '#fecaca',
    fontSize: '13px',
    margin: 0,
  },
};

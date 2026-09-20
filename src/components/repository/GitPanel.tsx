import React, { useState, useEffect, useMemo } from 'react';
import { fetchRepositoryGit } from '@/api/client';
import type {
  RepositoryGitResponse,
} from '@/types/repository';

interface GitPanelProps {
  repoId?: string;
  onSelectFile?: (path: string) => void;
}

type TabType = 'commits' | 'contributors' | 'hotspots' | 'timeline';

export const GitPanel: React.FC<GitPanelProps> = ({
  repoId,
  onSelectFile,
}) => {
  const [data, setData] = useState<RepositoryGitResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('commits');
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

    fetchRepositoryGit(repoId, 200)
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
              : 'Failed to fetch repository Git metadata.';
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

  // Filtered commits
  const filteredCommits = useMemo(() => {
    if (!data) return [];
    if (!searchQuery) return data.commits;
    const q = searchQuery.toLowerCase();
    return data.commits.filter(
      (c) =>
        c.hash.toLowerCase().includes(q) ||
        c.author_name.toLowerCase().includes(q) ||
        c.author_email.toLowerCase().includes(q) ||
        c.message.toLowerCase().includes(q)
    );
  }, [data, searchQuery]);

  // Filtered contributors
  const filteredContributors = useMemo(() => {
    if (!data) return [];
    if (!searchQuery) return data.contributors;
    const q = searchQuery.toLowerCase();
    return data.contributors.filter(
      (contrib) =>
        contrib.name.toLowerCase().includes(q) ||
        contrib.email.toLowerCase().includes(q)
    );
  }, [data, searchQuery]);

  // Filtered hotspots
  const filteredHotspots = useMemo(() => {
    if (!data) return [];
    if (!searchQuery) return data.top_changed_files;
    const q = searchQuery.toLowerCase();
    return data.top_changed_files.filter(
      (h) =>
        h.file_path.toLowerCase().includes(q) ||
        h.last_author.toLowerCase().includes(q)
    );
  }, [data, searchQuery]);

  // 1. Empty State (No Active Repo)
  if (!repoId) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.emptyPromptBox}>
          <div style={styles.emptyIconCircle}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="4" />
              <line x1="1.05" y1="12" x2="7" y2="12" />
              <line x1="17" y1="12" x2="22.95" y2="12" />
            </svg>
          </div>
          <h3 style={styles.emptyPromptTitle}>No Active Repository Selected</h3>
          <p style={styles.emptyPromptSubtext}>
            Upload a codebase archive on the Repository Scanner page to analyze Git commit history, contributor metrics, and file hotspots.
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
          <p style={styles.loadingText}>Analyzing Git history and metadata...</p>
        </div>
      </div>
    );
  }

  // 3. Error State
  if (error || !data) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.errorBox}>
          <h4 style={styles.errorTitle}>Git Intelligence Error</h4>
          <p style={styles.errorSubtext}>{error || 'Unable to load Git metadata.'}</p>
        </div>
      </div>
    );
  }

  const { summary } = data;

  // 4. No Git Metadata State (Valid repo, but missing .git directory)
  if (!summary.has_git_metadata) {
    return (
      <div style={styles.panelContainer}>
        <div style={styles.headerRow}>
          <div>
            <h2 style={styles.panelTitle}>Git Intelligence</h2>
            <p style={styles.panelSubtitle}>
              Commit history timeline, author contribution metrics, and file modification hotspots
            </p>
          </div>
          <span style={styles.noGitBadge}>No Git History</span>
        </div>

        <div style={styles.emptyPromptBox}>
          <div style={styles.emptyIconCircleWarning}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <h3 style={styles.emptyPromptTitle}>No Git Metadata Available</h3>
          <p style={styles.emptyPromptSubtext}>
            This repository archive does not contain Git metadata (.git directory was not included in the uploaded ZIP file).
          </p>
        </div>
      </div>
    );
  }

  const formatDate = (isoStr?: string | null) => {
    if (!isoStr) return 'N/A';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoStr;
    }
  };

  const formatFullDate = (isoStr?: string | null) => {
    if (!isoStr) return 'N/A';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div style={styles.panelContainer}>
      {/* Header */}
      <div style={styles.headerRow}>
        <div>
          <h2 style={styles.panelTitle}>Git Intelligence</h2>
          <p style={styles.panelSubtitle}>
            Static Git repository metadata, commit logs, author contribution metrics, and file hotspots
          </p>
        </div>
        <div style={styles.badgeGroup}>
          <span style={styles.verifiedBadge}>Git Repository Verified</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={styles.kpiGrid}>
        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Analyzed Commits</div>
          <div style={styles.kpiValue}>{summary.analyzed_commit_count}</div>
          <div style={styles.kpiSubtext}>Bounded commit history</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Contributors</div>
          <div style={styles.kpiValue}>{summary.total_contributors}</div>
          <div style={styles.kpiSubtext}>Unique authors</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>Current Branch</div>
          <div style={styles.kpiValueSm}>{summary.current_branch}</div>
          <div style={styles.kpiSubtext}>Active Git ref</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>HEAD Commit</div>
          <div style={styles.kpiValueCode}>
            {summary.head_commit_hash ? summary.head_commit_hash.substring(0, 7) : 'None'}
          </div>
          <div style={styles.kpiSubtext}>Latest commit SHA</div>
        </div>

        <div style={styles.kpiCard}>
          <div style={styles.kpiLabel}>History Span</div>
          <div style={styles.kpiValueText}>
            {formatDate(summary.oldest_commit_date)} – {formatDate(summary.newest_commit_date)}
          </div>
          <div style={styles.kpiSubtext}>Analyzed commit range</div>
        </div>
      </div>

      {/* Controls & Search */}
      <div style={styles.controlsRow}>
        <div style={styles.tabsContainer}>
          <button
            style={activeTab === 'commits' ? styles.tabActive : styles.tabInactive}
            onClick={() => setActiveTab('commits')}
          >
            Commit History ({data.commits.length})
          </button>
          <button
            style={activeTab === 'contributors' ? styles.tabActive : styles.tabInactive}
            onClick={() => setActiveTab('contributors')}
          >
            Contributors ({data.contributors.length})
          </button>
          <button
            style={activeTab === 'hotspots' ? styles.tabActive : styles.tabInactive}
            onClick={() => setActiveTab('hotspots')}
          >
            File Hotspots ({data.top_changed_files.length})
          </button>
          <button
            style={activeTab === 'timeline' ? styles.tabActive : styles.tabInactive}
            onClick={() => setActiveTab('timeline')}
          >
            Activity Timeline ({data.activity_timeline.length})
          </button>
        </div>

        <div style={styles.searchBox}>
          <input
            type="text"
            placeholder="Search commits, authors, or files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={styles.searchInput}
          />
        </div>
      </div>

      {/* TAB 1: Commit History */}
      {activeTab === 'commits' && (
        <div style={styles.sectionContainer}>
          {filteredCommits.length === 0 ? (
            <div style={styles.emptyStateContainer}>
              <p style={styles.emptyStateSubtext}>No commits match current search query.</p>
            </div>
          ) : (
            <div style={styles.commitsList}>
              {filteredCommits.map((c) => (
                <div key={c.hash} style={styles.commitCard}>
                  <div style={styles.commitHeader}>
                    <div style={styles.commitTitleRow}>
                      <span style={styles.shaBadge}>{c.short_hash}</span>
                      <span style={styles.commitMessage}>{c.message || 'No commit message'}</span>
                    </div>
                    <span style={styles.commitDate}>{formatFullDate(c.timestamp)}</span>
                  </div>

                  <div style={styles.commitMetaRow}>
                    <div style={styles.authorBadgeGroup}>
                      <div style={styles.authorAvatarCircle}>
                        {c.author_name.charAt(0).toUpperCase()}
                      </div>
                      <span style={styles.authorName}>{c.author_name}</span>
                      <span style={styles.authorEmail}>&lt;{c.author_email}&gt;</span>
                    </div>

                    <div style={styles.statsGroup}>
                      <span style={styles.statFiles}>{c.files_changed_count} files</span>
                      <span style={styles.statInsertions}>+{c.insertions}</span>
                      <span style={styles.statDeletions}>-{c.deletions}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Contributors */}
      {activeTab === 'contributors' && (
        <div style={styles.sectionContainer}>
          {filteredContributors.length === 0 ? (
            <div style={styles.emptyStateContainer}>
              <p style={styles.emptyStateSubtext}>No contributors match current search query.</p>
            </div>
          ) : (
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Contributor</th>
                    <th style={styles.th}>Email</th>
                    <th style={styles.th}>Analyzed Commits</th>
                    <th style={styles.th}>First Commit Date</th>
                    <th style={styles.th}>Latest Commit Date</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredContributors.map((contrib, i) => (
                    <tr key={i} style={styles.tr}>
                      <td style={styles.td}>
                        <div style={styles.authorTableCell}>
                          <div style={styles.authorAvatarCircleSm}>
                            {contrib.name.charAt(0).toUpperCase()}
                          </div>
                          <span style={styles.authorCellName}>{contrib.name}</span>
                        </div>
                      </td>
                      <td style={styles.tdMuted}>{contrib.email || 'N/A'}</td>
                      <td style={styles.tdHighlight}>{contrib.commit_count}</td>
                      <td style={styles.td}>{formatDate(contrib.first_commit_date)}</td>
                      <td style={styles.td}>{formatDate(contrib.last_commit_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: File Hotspots */}
      {activeTab === 'hotspots' && (
        <div style={styles.sectionContainer}>
          {filteredHotspots.length === 0 ? (
            <div style={styles.emptyStateContainer}>
              <p style={styles.emptyStateSubtext}>No file hotspots match current search query.</p>
            </div>
          ) : (
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>File Path</th>
                    <th style={styles.th}>Commits Count</th>
                    <th style={styles.th}>Latest Commit SHA</th>
                    <th style={styles.th}>Latest Author</th>
                    <th style={styles.th}>Latest Touch Date</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredHotspots.map((h, i) => (
                    <tr key={i} style={styles.tr}>
                      <td style={styles.td}>
                        <button
                          style={styles.fileLinkButton}
                          onClick={() => onSelectFile && onSelectFile(h.file_path)}
                        >
                          {h.file_path}
                        </button>
                      </td>
                      <td style={styles.tdHighlight}>{h.commit_count}</td>
                      <td style={styles.td}>
                        <span style={styles.shaBadgeSm}>{h.last_commit_hash}</span>
                      </td>
                      <td style={styles.td}>{h.last_author}</td>
                      <td style={styles.td}>{formatDate(h.last_commit_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Activity Timeline */}
      {activeTab === 'timeline' && (
        <div style={styles.sectionContainer}>
          {data.activity_timeline.length === 0 ? (
            <div style={styles.emptyStateContainer}>
              <p style={styles.emptyStateSubtext}>No commit activity points available.</p>
            </div>
          ) : (
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Date</th>
                    <th style={styles.th}>Commits Authored</th>
                    <th style={styles.th}>Activity Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {data.activity_timeline.map((point, i) => {
                    const maxCount = Math.max(
                      ...data.activity_timeline.map((p) => p.commit_count)
                    );
                    const barWidth =
                      maxCount > 0 ? (point.commit_count / maxCount) * 100 : 0;
                    return (
                      <tr key={i} style={styles.tr}>
                        <td style={styles.tdMono}>{point.date}</td>
                        <td style={styles.tdHighlight}>{point.commit_count}</td>
                        <td style={styles.td}>
                          <div style={styles.barContainer}>
                            <div
                              style={{
                                ...styles.barFill,
                                width: `${Math.max(barWidth, 4)}%`,
                              }}
                            />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
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
  verifiedBadge: {
    padding: '4px 10px',
    backgroundColor: '#064e3b',
    color: '#34d399',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '600',
    border: '1px solid #059669',
  },
  noGitBadge: {
    padding: '4px 10px',
    backgroundColor: '#451a03',
    color: '#fde047',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '600',
    border: '1px solid #d97706',
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
    fontSize: '18px',
    fontWeight: '700',
    color: '#a855f7',
    wordBreak: 'break-word',
  },
  kpiValueCode: {
    fontSize: '22px',
    fontWeight: '700',
    fontFamily: 'monospace',
    color: '#34d399',
  },
  kpiValueText: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#cbd5e1',
  },
  kpiSubtext: {
    fontSize: '12px',
    color: '#64748b',
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
  commitsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  commitCard: {
    backgroundColor: '#1e293b',
    borderRadius: '8px',
    padding: '16px',
    border: '1px solid #334155',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  commitHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '8px',
  },
  commitTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  shaBadge: {
    padding: '3px 8px',
    backgroundColor: '#0f172a',
    color: '#38bdf8',
    borderRadius: '4px',
    fontFamily: 'monospace',
    fontSize: '12px',
    fontWeight: '700',
    border: '1px solid #0284c7',
  },
  shaBadgeSm: {
    padding: '2px 6px',
    backgroundColor: '#0f172a',
    color: '#38bdf8',
    borderRadius: '4px',
    fontFamily: 'monospace',
    fontSize: '11px',
    fontWeight: '600',
  },
  commitMessage: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#f8fafc',
  },
  commitDate: {
    fontSize: '12px',
    color: '#64748b',
  },
  commitMetaRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '8px',
  },
  authorBadgeGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  authorAvatarCircle: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    backgroundColor: '#0284c7',
    color: '#ffffff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '11px',
    fontWeight: '700',
  },
  authorAvatarCircleSm: {
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    backgroundColor: '#0284c7',
    color: '#ffffff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '10px',
    fontWeight: '700',
  },
  authorTableCell: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  authorName: {
    fontSize: '13px',
    color: '#cbd5e1',
    fontWeight: '500',
  },
  authorCellName: {
    fontSize: '13px',
    color: '#f8fafc',
    fontWeight: '600',
  },
  authorEmail: {
    fontSize: '12px',
    color: '#64748b',
  },
  statsGroup: {
    display: 'flex',
    gap: '12px',
    fontSize: '12px',
    fontWeight: '600',
  },
  statFiles: {
    color: '#94a3b8',
  },
  statInsertions: {
    color: '#34d399',
  },
  statDeletions: {
    color: '#fca5a5',
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
  tdMuted: {
    padding: '12px 16px',
    color: '#64748b',
    fontFamily: 'monospace',
    fontSize: '12px',
  },
  tdMono: {
    padding: '12px 16px',
    color: '#cbd5e1',
    fontFamily: 'monospace',
  },
  tdHighlight: {
    padding: '12px 16px',
    color: '#38bdf8',
    fontWeight: '700',
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
  barContainer: {
    width: '100%',
    maxWidth: '200px',
    height: '10px',
    backgroundColor: '#1e293b',
    borderRadius: '5px',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    backgroundColor: '#38bdf8',
    borderRadius: '5px',
  },
  emptyStateContainer: {
    padding: '40px 20px',
    textAlign: 'center',
    backgroundColor: '#1e293b',
    borderRadius: '8px',
    border: '1px solid #334155',
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
  emptyIconCircleWarning: {
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    backgroundColor: '#451a03',
    color: '#fde047',
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

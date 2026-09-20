import React, { useState, useEffect } from 'react';
import {
  getStoredRepositories,
  getActiveRepositoryId,
  setActiveRepositoryId,
  removeStoredRepository,
  REPO_CHANGED_EVENT,
  type StoredRepositoryItem,
} from '@/utils/repositorySession';

interface ExistingRepositoriesSectionProps {
  onAddFirstRepo: () => void;
}

export const ExistingRepositoriesSection: React.FC<ExistingRepositoriesSectionProps> = ({
  onAddFirstRepo,
}) => {
  const [repositories, setRepositories] = useState<StoredRepositoryItem[]>([]);
  const [activeRepoId, setActiveRepoId] = useState<string | null>(null);

  const refreshState = () => {
    setRepositories(getStoredRepositories());
    setActiveRepoId(getActiveRepositoryId());
  };

  useEffect(() => {
    refreshState();

    const handleRepoChanged = () => {
      refreshState();
    };

    window.addEventListener(REPO_CHANGED_EVENT, handleRepoChanged);
    window.addEventListener('storage', handleRepoChanged);

    return () => {
      window.removeEventListener(REPO_CHANGED_EVENT, handleRepoChanged);
      window.removeEventListener('storage', handleRepoChanged);
    };
  }, []);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleSelectActive = (repoId: string) => {
    setActiveRepositoryId(repoId);
  };

  const handleRemoveRepo = (e: React.MouseEvent, repoId: string) => {
    e.stopPropagation();
    removeStoredRepository(repoId);
  };

  const totalCount = repositories.length;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.sectionHeader}>
        <h3 style={styles.sectionTitle}>Existing Repositories</h3>
        <span style={styles.countBadge}>
          {totalCount} {totalCount === 1 ? 'Repository' : 'Repositories'}
        </span>
      </div>

      {totalCount === 0 ? (
        /* Empty State */
        <div style={styles.emptyStateCard}>
          <div style={styles.iconCircle}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
          </div>

          <h4 style={styles.emptyTitle}>No repositories yet</h4>
          <p style={styles.emptySubtext}>Your analyzed repositories will appear here once connected.</p>

          <button style={styles.addFirstBtn} onClick={onAddFirstRepo}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Add your first repository
          </button>
        </div>
      ) : (
        /* Populated Repositories Grid */
        <div style={styles.reposGrid}>
          {repositories.map((repo) => {
            const isActive = repo.repo_id === activeRepoId;
            const langEntries = Object.entries(repo.detected_languages || {});

            return (
              <div
                key={repo.repo_id}
                style={{
                  ...styles.repoCard,
                  ...(isActive ? styles.repoCardActive : {}),
                }}
                onClick={() => !isActive && handleSelectActive(repo.repo_id)}
              >
                <div style={styles.repoCardHeader}>
                  <div style={styles.titleGroup}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2">
                      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                    </svg>
                    <span style={styles.repoFilename}>{repo.filename}</span>
                  </div>

                  <div style={styles.headerActions}>
                    {isActive ? (
                      <span style={styles.activeBadge}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        Active Repository
                      </span>
                    ) : (
                      <button
                        type="button"
                        style={styles.selectActiveBtn}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectActive(repo.repo_id);
                        }}
                      >
                        Select as Active
                      </button>
                    )}

                    <button
                      type="button"
                      style={styles.removeBtn}
                      onClick={(e) => handleRemoveRepo(e, repo.repo_id)}
                      title="Remove repository from local session list"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div style={styles.metaRow}>
                  <span>
                    Files: <strong>{repo.total_files}</strong>
                  </span>
                  <span>•</span>
                  <span>
                    Size: <strong>{formatFileSize(repo.size)}</strong>
                  </span>
                  {repo.uploaded_at && (
                    <>
                      <span>•</span>
                      <span>
                        Uploaded: <strong>{repo.uploaded_at}</strong>
                      </span>
                    </>
                  )}
                </div>

                {langEntries.length > 0 && (
                  <div style={styles.languagesRow}>
                    {langEntries.map(([lang, count]) => (
                      <span key={lang} style={styles.langPill}>
                        {lang}: {count}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginTop: '40px',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '16px',
  },
  sectionTitle: {
    fontSize: '16px',
    fontWeight: 700,
    color: 'var(--text-main)',
  },
  countBadge: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    padding: '3px 10px',
    borderRadius: 'var(--radius-full)',
    border: '1px solid var(--border-subtle)',
  },
  emptyStateCard: {
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    padding: '48px 24px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    boxShadow: 'var(--shadow-xs)',
  },
  iconCircle: {
    width: '48px',
    height: '48px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--bg-app)',
    color: 'var(--text-subtle)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '14px',
    border: '1px solid var(--border-subtle)',
  },
  emptyTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--text-main)',
    marginBottom: '6px',
  },
  emptySubtext: {
    fontSize: '13.5px',
    color: 'var(--text-muted)',
    marginBottom: '20px',
  },
  addFirstBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 16px',
    backgroundColor: 'var(--color-primary-light)',
    color: 'var(--color-primary)',
    fontWeight: 600,
    fontSize: '13px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-subtle)',
    cursor: 'pointer',
    transition: 'background-color var(--transition-fast)',
  },
  reposGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  repoCard: {
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    padding: '16px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  repoCardActive: {
    borderColor: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
  },
  repoCardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    flexWrap: 'wrap',
  },
  titleGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  repoFilename: {
    fontSize: '15px',
    fontWeight: 700,
    color: 'var(--text-main)',
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  activeBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '11.5px',
    fontWeight: 700,
    color: 'var(--color-success)',
    backgroundColor: 'var(--color-success-bg)',
    padding: '3px 10px',
    borderRadius: 'var(--radius-full)',
    border: '1px solid #A7F3D0',
    textTransform: 'uppercase',
  },
  selectActiveBtn: {
    padding: '4px 10px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--color-primary)',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--color-primary)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  removeBtn: {
    padding: '4px 8px',
    backgroundColor: 'transparent',
    border: 'none',
    color: 'var(--text-subtle)',
    cursor: 'pointer',
    borderRadius: 'var(--radius-sm)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  metaRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12.5px',
    color: 'var(--text-muted)',
    flexWrap: 'wrap',
  },
  languagesRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap',
    marginTop: '2px',
  },
  langPill: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-main)',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-sm)',
  },
};

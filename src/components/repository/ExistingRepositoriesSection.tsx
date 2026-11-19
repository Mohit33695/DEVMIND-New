import React, { useState, useEffect } from 'react';
import {
  getStoredRepositories,
  getActiveRepositoryId,
  setActiveRepositoryId,
  syncRepositoriesWithBackend,
  deleteStoredRepository,
  REPO_CHANGED_EVENT,
  type StoredRepositoryItem,
} from '@/utils/repositorySession';

interface ExistingRepositoriesSectionProps {
  onAddFirstRepo: () => void;
}

export const ExistingRepositoriesSection: React.FC<ExistingRepositoriesSectionProps> = ({
  onAddFirstRepo,
}) => {
  const [repositories, setRepositories] = useState<StoredRepositoryItem[]>(() => getStoredRepositories());
  const [activeRepoId, setActiveRepoId] = useState<string | null>(() => getActiveRepositoryId());
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Deletion Confirmation Modal State
  const [repoToDelete, setRepoToDelete] = useState<StoredRepositoryItem | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const refreshState = () => {
    setRepositories(getStoredRepositories());
    setActiveRepoId(getActiveRepositoryId());
  };

  const handleSyncWithBackend = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const synced = await syncRepositoriesWithBackend();
      setRepositories(synced);
      setActiveRepoId(getActiveRepositoryId());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to synchronize repositories from backend.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    handleSyncWithBackend();

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

  const handleOpenDeleteModal = (e: React.MouseEvent, repo: StoredRepositoryItem) => {
    e.stopPropagation();
    setDeleteError(null);
    setRepoToDelete(repo);
  };

  const handleCloseDeleteModal = () => {
    if (isDeleting) return;
    setRepoToDelete(null);
    setDeleteError(null);
  };

  const handleConfirmDelete = async () => {
    if (!repoToDelete) return;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteStoredRepository(repoToDelete.repo_id);
      setRepoToDelete(null);
      await handleSyncWithBackend();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete repository from backend.';
      setDeleteError(msg);
    } finally {
      setIsDeleting(false);
    }
  };

  const totalCount = repositories.length;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.sectionHeader}>
        <div style={styles.headerLeft}>
          <h3 style={styles.sectionTitle}>Existing Repositories</h3>
          <span style={styles.countBadge}>
            {totalCount} {totalCount === 1 ? 'Repository' : 'Repositories'}
          </span>
        </div>

        <button
          type="button"
          style={styles.refreshBtn}
          onClick={handleSyncWithBackend}
          disabled={isLoading}
          title="Refresh repository list from backend"
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            style={{
              animation: isLoading ? 'spin 1s linear infinite' : 'none',
            }}
          >
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
          </svg>
          {isLoading ? 'Syncing...' : 'Refresh'}
        </button>
      </div>

      {/* Sync Error Banner */}
      {error && (
        <div style={styles.errorBanner} role="alert">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{error}</span>
          <button style={styles.retryBtn} onClick={handleSyncWithBackend}>
            Retry
          </button>
        </div>
      )}

      {totalCount === 0 && !isLoading ? (
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
            const isIndexed = repo.indexing_status === 'indexed';

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
                    <span style={styles.repoIdPill} title={`Repository ID: ${repo.repo_id}`}>
                      {repo.repo_id.slice(0, 8)}...
                    </span>
                  </div>

                  <div style={styles.headerActions}>
                    {isIndexed ? (
                      <span style={styles.indexedBadge} title="RAG vector search is ready for this repository">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        RAG Indexed
                      </span>
                    ) : (
                      <span style={styles.notIndexedBadge} title="Repository source files stored; RAG indexing pending">
                        Not Indexed
                      </span>
                    )}

                    {isActive ? (
                      <span style={styles.activeBadge}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        Active
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
                      onClick={(e) => handleOpenDeleteModal(e, repo)}
                      title="Permanently delete repository data and index"
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
                        Uploaded: <strong>{new Date(repo.uploaded_at).toLocaleString()}</strong>
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

      {/* Deletion Confirmation Modal */}
      {repoToDelete && (
        <div style={styles.modalOverlay} onClick={handleCloseDeleteModal}>
          <div style={styles.modalCard} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div style={styles.warningIconCircle}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-error)" strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </div>
              <h4 style={styles.modalTitle}>Delete Repository?</h4>
            </div>

            <p style={styles.modalText}>
              Are you sure you want to permanently delete <strong>{repoToDelete.filename}</strong>?
            </p>
            <p style={styles.modalSubtext}>
              This action will remove all extracted source files, symbol metadata, and vector index files from managed storage. This cannot be undone.
            </p>

            {deleteError && (
              <div style={styles.deleteErrorBanner}>
                {deleteError}
              </div>
            )}

            <div style={styles.modalActions}>
              <button
                type="button"
                style={styles.modalCancelBtn}
                onClick={handleCloseDeleteModal}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                style={styles.modalConfirmBtn}
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
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
    flexWrap: 'wrap',
    gap: '12px',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
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
  refreshBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '5px 12px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 14px',
    backgroundColor: 'var(--color-error-bg)',
    color: 'var(--color-error)',
    border: '1px solid var(--color-error)',
    borderRadius: 'var(--radius-md)',
    fontSize: '13px',
    marginBottom: '16px',
  },
  retryBtn: {
    marginLeft: 'auto',
    padding: '2px 8px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--color-error)',
    backgroundColor: 'transparent',
    border: '1px solid var(--color-error)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
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
  repoIdPill: {
    fontSize: '11px',
    color: 'var(--text-subtle)',
    backgroundColor: 'var(--bg-app)',
    padding: '2px 6px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-subtle)',
    fontFamily: 'monospace',
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  indexedBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    fontWeight: 600,
    color: '#0284c7',
    backgroundColor: '#e0f2fe',
    border: '1px solid #bae6fd',
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
  },
  notIndexedBadge: {
    fontSize: '11px',
    color: 'var(--text-subtle)',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-subtle)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
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
    transition: 'color var(--transition-fast)',
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
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.65)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '16px',
  },
  modalCard: {
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    padding: '24px',
    maxWidth: '460px',
    width: '100%',
    boxShadow: 'var(--shadow-lg)',
  },
  modalHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '14px',
  },
  warningIconCircle: {
    width: '38px',
    height: '38px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--color-error-bg)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: 'var(--text-main)',
    margin: 0,
  },
  modalText: {
    fontSize: '14px',
    color: 'var(--text-main)',
    marginBottom: '8px',
    lineHeight: '1.5',
  },
  modalSubtext: {
    fontSize: '12.5px',
    color: 'var(--text-muted)',
    marginBottom: '20px',
    lineHeight: '1.4',
  },
  deleteErrorBanner: {
    padding: '8px 12px',
    backgroundColor: 'var(--color-error-bg)',
    color: 'var(--color-error)',
    borderRadius: 'var(--radius-md)',
    fontSize: '12.5px',
    marginBottom: '16px',
  },
  modalActions: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: '10px',
  },
  modalCancelBtn: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  modalConfirmBtn: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 600,
    color: '#ffffff',
    backgroundColor: 'var(--color-error)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
};

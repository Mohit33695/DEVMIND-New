import React, { useState, useEffect, useRef } from 'react';
import { UploadCard } from '@/components/repository/UploadCard';
import { SecurityPanel } from '@/components/repository/SecurityPanel';
import { ExistingRepositoriesSection } from '@/components/repository/ExistingRepositoriesSection';
import { AnalysisPipelineSection } from '@/components/repository/AnalysisPipelineSection';
import { RepositoryExplorer } from '@/components/repository/RepositoryExplorer';
import { fetchRepositoryDetail } from '@/api/client';
import type { RepositoryDetailResponse } from '@/types/repository';
import {
  getActiveRepositoryId,
  syncRepositoriesWithBackend,
  REPO_CHANGED_EVENT,
} from '@/utils/repositorySession';

export const RepositoryPage: React.FC = () => {
  const [activeRepoId, setActiveRepoId] = useState<string | null>(() => getActiveRepositoryId());
  const [repoDetail, setRepoDetail] = useState<RepositoryDetailResponse | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [showUploadCard, setShowUploadCard] = useState<boolean>(false);

  const uploadSectionRef = useRef<HTMLDivElement | null>(null);
  const reposSectionRef = useRef<HTMLDivElement | null>(null);

  // Sync repositories with backend on initial mount
  useEffect(() => {
    syncRepositoriesWithBackend().then(() => {
      setActiveRepoId(getActiveRepositoryId());
    });

    const handleRepoChanged = () => {
      setActiveRepoId(getActiveRepositoryId());
    };

    window.addEventListener(REPO_CHANGED_EVENT, handleRepoChanged);
    window.addEventListener('storage', handleRepoChanged);

    return () => {
      window.removeEventListener(REPO_CHANGED_EVENT, handleRepoChanged);
      window.removeEventListener('storage', handleRepoChanged);
    };
  }, []);

  // Fetch full repository details and file tree whenever activeRepoId changes
  useEffect(() => {
    if (!activeRepoId) {
      setRepoDetail(null);
      setDetailError(null);
      setIsLoadingDetail(false);
      return;
    }

    let isMounted = true;
    setIsLoadingDetail(true);
    setDetailError(null);

    fetchRepositoryDetail(activeRepoId)
      .then((data) => {
        if (isMounted) {
          setRepoDetail(data);
          setShowUploadCard(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to retrieve repository details.';
          setDetailError(msg);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingDetail(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [activeRepoId]);

  const handleScrollToUpload = () => {
    setShowUploadCard(true);
    setTimeout(() => {
      uploadSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  };

  const handleScrollToRepos = () => {
    reposSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div style={styles.pageContainer}>
      {/* 1. Page Heading */}
      <div style={styles.pageHeader}>
        <div style={styles.engineLabel}>DevMind Code Engine</div>
        <h1 style={styles.heading}>Repository Intelligence</h1>
        <p style={styles.subheading}>
          Explore repository code structure, syntax symbols, static dependencies, and indexing status.
        </p>
      </div>

      {/* 2. Active Repository Overview Banner (when an active repo exists) */}
      {activeRepoId && repoDetail && !isLoadingDetail && (
        <div style={styles.activeRepoBanner}>
          <div style={styles.activeRepoLeft}>
            <div style={styles.activeRepoIcon}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              </svg>
            </div>
            <div>
              <div style={styles.activeRepoTitleRow}>
                <h2 style={styles.activeRepoTitle}>{repoDetail.filename}</h2>
                <span style={styles.activeStatusPill}>
                  <span style={styles.greenDot} />
                  Active
                </span>
                {repoDetail.indexing_status === 'indexed' && (
                  <span style={styles.indexedPill}>RAG Ready</span>
                )}
              </div>
              <div style={styles.activeRepoMeta}>
                <span>ID: <code style={styles.codeSnippet}>{repoDetail.repo_id.slice(0, 12)}...</code></span>
                <span>•</span>
                <span>Files: <strong>{repoDetail.scan_result.total_files}</strong></span>
                <span>•</span>
                <span>Size: <strong>{formatFileSize(repoDetail.size)}</strong></span>
                {repoDetail.uploaded_at && (
                  <>
                    <span>•</span>
                    <span>Uploaded: <strong>{new Date(repoDetail.uploaded_at).toLocaleDateString()}</strong></span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div style={styles.activeRepoActions}>
            <button
              type="button"
              style={styles.switchRepoBtn}
              onClick={handleScrollToRepos}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="17 1 21 5 17 9" />
                <path d="M3 11V9a4 4 0 0 1 4-4h14" />
                <polyline points="7 23 3 19 7 15" />
                <path d="M21 13v2a4 4 0 0 1-4 4H3" />
              </svg>
              Switch Repository
            </button>

            <button
              type="button"
              style={styles.uploadNewToggleBtn}
              onClick={() => setShowUploadCard((prev) => !prev)}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              {showUploadCard ? 'Hide Upload Form' : 'Upload New'}
            </button>
          </div>
        </div>
      )}

      {/* Loading Repository Detail State */}
      {isLoadingDetail && (
        <div style={styles.loadingBanner}>
          <div style={styles.spinner} />
          <span>Loading repository structure and file tree...</span>
        </div>
      )}

      {/* Detail Error Banner */}
      {detailError && (
        <div style={styles.errorBanner} role="alert">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <div style={{ flex: 1 }}>
            <strong>Error loading repository details:</strong> {detailError}
          </div>
          <button
            type="button"
            style={styles.retryBtn}
            onClick={() => {
              if (activeRepoId) {
                setIsLoadingDetail(true);
                setDetailError(null);
                fetchRepositoryDetail(activeRepoId)
                  .then(setRepoDetail)
                  .catch((e) => setDetailError(e instanceof Error ? e.message : 'Failed'))
                  .finally(() => setIsLoadingDetail(false));
              }
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* 3. Upload Dropzone Card (shown when toggled or when no active repo) */}
      {(showUploadCard || !activeRepoId) && (
        <div ref={uploadSectionRef} style={styles.sectionSpacing}>
          <UploadCard onUploadSuccess={() => setShowUploadCard(false)} />
        </div>
      )}

      {/* 4. Repository Explorer for Active Repository */}
      {repoDetail && !isLoadingDetail && (
        <div style={styles.sectionSpacing}>
          <RepositoryExplorer
            key={repoDetail.repo_id}
            scanResult={repoDetail.scan_result}
            filename={repoDetail.filename}
            repoId={repoDetail.repo_id}
          />
        </div>
      )}

      {/* 5. Security Information Panel */}
      <SecurityPanel repoId={activeRepoId || undefined} />

      {/* 6. Existing Repositories Section */}
      <div ref={reposSectionRef}>
        <ExistingRepositoriesSection onAddFirstRepo={handleScrollToUpload} />
      </div>

      {/* 7. How Repository Analysis Works Pipeline */}
      <AnalysisPipelineSection />
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  pageContainer: {
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  pageHeader: {
    marginBottom: '24px',
  },
  engineLabel: {
    fontSize: '11.5px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.6px',
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    padding: '3px 10px',
    borderRadius: 'var(--radius-full)',
    display: 'inline-block',
    marginBottom: '10px',
  },
  heading: {
    fontSize: '28px',
    fontWeight: 700,
    color: 'var(--text-main)',
    marginBottom: '8px',
  },
  subheading: {
    fontSize: '15px',
    color: 'var(--text-muted)',
    lineHeight: '1.5',
    maxWidth: '680px',
  },
  sectionSpacing: {
    marginBottom: '24px',
  },
  activeRepoBanner: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    padding: '16px 20px',
    marginBottom: '24px',
    boxShadow: 'var(--shadow-xs)',
    flexWrap: 'wrap',
    gap: '16px',
  },
  activeRepoLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
  },
  activeRepoIcon: {
    width: '42px',
    height: '42px',
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'var(--color-primary-light)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  activeRepoTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap',
  },
  activeRepoTitle: {
    fontSize: '17px',
    fontWeight: 700,
    color: 'var(--text-main)',
    margin: 0,
  },
  activeStatusPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '11px',
    fontWeight: 700,
    color: 'var(--color-success)',
    backgroundColor: 'var(--color-success-bg)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
    border: '1px solid #a7f3d0',
    textTransform: 'uppercase',
  },
  greenDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: 'var(--color-success)',
  },
  indexedPill: {
    fontSize: '11px',
    fontWeight: 600,
    color: '#0284c7',
    backgroundColor: '#e0f2fe',
    border: '1px solid #bae6fd',
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
  },
  activeRepoMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12.5px',
    color: 'var(--text-muted)',
    marginTop: '4px',
    flexWrap: 'wrap',
  },
  codeSnippet: {
    backgroundColor: 'var(--bg-app)',
    padding: '1px 5px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-subtle)',
    fontFamily: 'monospace',
  },
  activeRepoActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  switchRepoBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '7px 14px',
    fontSize: '12.5px',
    fontWeight: 600,
    color: 'var(--text-main)',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  uploadNewToggleBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '7px 14px',
    fontSize: '12.5px',
    fontWeight: 600,
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  loadingBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '24px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-muted)',
    fontSize: '14px',
    marginBottom: '24px',
    justifyContent: 'center',
  },
  spinner: {
    width: '18px',
    height: '18px',
    border: '2px solid var(--border-default)',
    borderTopColor: 'var(--color-primary)',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '14px 18px',
    backgroundColor: 'var(--color-error-bg)',
    color: 'var(--color-error)',
    border: '1px solid var(--color-error)',
    borderRadius: 'var(--radius-md)',
    fontSize: '13.5px',
    marginBottom: '24px',
  },
  retryBtn: {
    padding: '4px 12px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--color-error)',
    backgroundColor: 'transparent',
    border: '1px solid var(--color-error)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
};

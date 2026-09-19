import React, { useState, useRef } from 'react';
import type { DragEvent, ChangeEvent, KeyboardEvent } from 'react';
import { uploadRepositoryZip, type RepositoryUploadResponse } from '@/api/client';
import { RepositoryExplorer } from '@/components/repository/RepositoryExplorer';


const MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024; // 200 MB

interface ValidationError {
  title: string;
  message: string;
}

export const UploadCard: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<ValidationError | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<RepositoryUploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Helper function to format file sizes cleanly (B, KB, MB)
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Client-side file validation logic
  const validateAndSetFile = (file: File) => {
    setError(null);
    setUploadResult(null);
    setUploadError(null);

    // 1. Extension check (.zip)
    const hasZipExtension = file.name.toLowerCase().endsWith('.zip');
    if (!hasZipExtension) {
      setError({
        title: 'Invalid file type',
        message: 'Please select a .zip repository archive.',
      });
      setSelectedFile(null);
      return;
    }

    // 2. Maximum file size check (200 MB)
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setError({
        title: 'File is too large',
        message: 'Repository archives must be 200 MB or smaller.',
      });
      setSelectedFile(null);
      return;
    }

    // File passed client validation
    setSelectedFile(file);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  // Drag and drop event handlers
  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragOver) setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleKeyDownDropZone = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleBrowseClick();
    }
  };

  const handleChangeFile = () => {
    setSelectedFile(null);
    setError(null);
    setUploadResult(null);
    setUploadError(null);
    setIsUploading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    // Re-open browser file picker
    setTimeout(() => {
      fileInputRef.current?.click();
    }, 50);
  };

  const handleStartAnalysis = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadResult(null);

    try {
      const result = await uploadRepositoryZip(selectedFile);
      setUploadResult(result);
      if (result.repo_id) {
        sessionStorage.setItem('devmind_active_repo_id', result.repo_id);
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed due to a server error.';
      setUploadError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div style={styles.cardContainer}>
      {/* Hidden real HTML file input */}
      <input
        type="file"
        ref={fileInputRef}
        accept=".zip"
        onChange={handleFileChange}
        aria-label="Select ZIP repository archive"
        style={{ display: 'none' }}
      />

      {!selectedFile ? (
        <div
          role="button"
          tabIndex={0}
          aria-label="Upload repository ZIP archive drop zone"
          onClick={handleBrowseClick}
          onKeyDown={handleKeyDownDropZone}
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            ...styles.dropZone,
            ...(isDragOver ? styles.dropZoneActive : {}),
          }}
        >
          <div style={styles.iconCircle}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
              <line x1="12" y1="22.08" x2="12" y2="12" />
            </svg>
          </div>

          <h3 style={styles.dropTitle}>Drop your repository ZIP here</h3>
          <p style={styles.dropSubtext}>or select a local compressed archive from your device</p>

          <button
            type="button"
            style={styles.browseButton}
            onClick={(e) => {
              e.stopPropagation(); // prevent parent click duplication
              handleBrowseClick();
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Browse files
          </button>

          <div style={styles.constraintsRow}>
            <span style={styles.constraintBadge}>ZIP only</span>
            <span style={styles.constraintDot}>•</span>
            <span style={styles.constraintBadge}>Max size: 200 MB</span>
            <span style={styles.constraintDot}>•</span>
            <span style={styles.constraintBadge}>SHA-256 verification planned</span>
          </div>

          {/* Validation Error Banner */}
          {error && (
            <div role="alert" aria-live="polite" style={styles.errorBanner}>
              <div style={styles.errorIconBox}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
              <div style={styles.errorContent}>
                <span style={styles.errorTitle}>{error.title}</span>
                <span style={styles.errorMessage}>{error.message}</span>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Selected File State */
        <div style={styles.selectedContainer}>
          <div style={styles.fileCard}>
            <div style={styles.fileCardLeft}>
              <div style={styles.fileIconBox}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                </svg>
              </div>

              <div style={styles.fileMeta}>
                <div style={styles.fileNameRow}>
                  <span style={styles.fileName}>{selectedFile.name}</span>
                  <span style={styles.fileSize}>({formatFileSize(selectedFile.size)})</span>
                </div>
                <div style={styles.validationBadge}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  Validation passed
                </div>
              </div>
            </div>

            <button type="button" style={styles.changeFileBtn} onClick={handleChangeFile} disabled={isUploading}>
              Change file
            </button>
          </div>

          {/* Backend Upload Errors */}
          {uploadError && (
            <div role="alert" aria-live="polite" style={styles.errorBanner}>
              <div style={styles.errorIconBox}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
              <div style={styles.errorContent}>
                <span style={styles.errorTitle}>Upload Error</span>
                <span style={styles.errorMessage}>{uploadError}</span>
              </div>
            </div>
          )}

          {/* Start Analysis Button / Uploading State / Upload Result */}
          {!uploadResult ? (
            <div style={styles.actionRow}>
              <button
                type="button"
                style={{
                  ...styles.startAnalysisBtn,
                  ...(isUploading ? styles.btnDisabled : {}),
                }}
                onClick={handleStartAnalysis}
                disabled={isUploading}
              >
                {isUploading ? (
                  <>
                    <span style={styles.spinnerDot} />
                    Uploading repository archive...
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <polygon points="5 3 19 12 5 21 5 3" />
                    </svg>
                    Start Analysis
                  </>
                )}
              </button>
            </div>
          ) : (
            <>
              <div role="status" aria-live="polite" style={styles.analysisSuccessBanner}>
                <div style={styles.readyBannerHeader}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ color: 'var(--color-success)' }}>
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span style={styles.successBadge}>Backend Validated</span>
                </div>
                <p style={styles.readyBannerText}>{uploadResult.message}</p>
                <div style={styles.resultMeta}>
                  <span>Filename: <strong>{uploadResult.filename}</strong></span>
                  <span>•</span>
                  <span>Size: <strong>{formatFileSize(uploadResult.size)}</strong></span>
                  <span>•</span>
                  <span>Status: <strong style={{ color: 'var(--color-success)' }}>{uploadResult.status}</strong></span>
                </div>
              </div>

              {uploadResult.scan_result && (
                <RepositoryExplorer
                  scanResult={uploadResult.scan_result}
                  filename={uploadResult.filename}
                  repoId={uploadResult.repo_id}
                />
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  cardContainer: {
    backgroundColor: 'var(--bg-surface)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    boxShadow: 'var(--shadow-sm)',
    overflow: 'hidden',
  },
  dropZone: {
    padding: '48px 32px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    border: '2px dashed var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    margin: '12px',
    backgroundColor: 'var(--bg-app)',
    transition: 'all var(--transition-normal)',
    cursor: 'pointer',
    outline: 'none',
  },
  dropZoneActive: {
    borderColor: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
  },
  iconCircle: {
    width: '56px',
    height: '56px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--color-primary-light)',
    color: 'var(--color-primary)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '16px',
  },
  dropTitle: {
    fontSize: '17px',
    fontWeight: 700,
    color: 'var(--text-main)',
    marginBottom: '6px',
  },
  dropSubtext: {
    fontSize: '14px',
    color: 'var(--text-muted)',
    marginBottom: '20px',
  },
  browseButton: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    padding: '9px 20px',
    backgroundColor: 'var(--color-primary)',
    color: 'var(--text-on-primary)',
    fontWeight: 600,
    fontSize: '13.5px',
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--shadow-xs)',
    marginBottom: '24px',
    transition: 'background-color var(--transition-fast)',
    border: 'none',
    cursor: 'pointer',
  },
  constraintsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    color: 'var(--text-subtle)',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  constraintBadge: {
    fontWeight: 500,
  },
  constraintDot: {
    color: 'var(--border-default)',
  },
  errorBanner: {
    marginTop: '20px',
    padding: '12px 16px',
    backgroundColor: 'var(--color-error-bg)',
    color: 'var(--color-error)',
    border: '1px solid #FCA5A5',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    textAlign: 'left',
    width: '100%',
    maxWidth: '480px',
  },
  errorIconBox: {
    marginTop: '1px',
    flexShrink: 0,
  },
  errorContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  errorTitle: {
    fontSize: '13.5px',
    fontWeight: 700,
    color: 'var(--color-error)',
  },
  errorMessage: {
    fontSize: '13px',
    color: 'var(--text-main)',
  },
  selectedContainer: {
    padding: '28px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  fileCard: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    gap: '16px',
    flexWrap: 'wrap',
  },
  fileCardLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
  },
  fileIconBox: {
    width: '42px',
    height: '42px',
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'var(--color-primary-light)',
    color: 'var(--color-primary)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  fileMeta: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  fileNameRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  fileName: {
    fontSize: '14.5px',
    fontWeight: 600,
    color: 'var(--text-main)',
  },
  fileSize: {
    fontSize: '13px',
    color: 'var(--text-muted)',
  },
  validationBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '11.5px',
    fontWeight: 600,
    color: 'var(--color-success)',
    backgroundColor: 'var(--color-success-bg)',
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
  },
  changeFileBtn: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    padding: '6px 12px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-surface)',
    cursor: 'pointer',
  },
  actionRow: {
    display: 'flex',
    justifyContent: 'flex-end',
  },
  startAnalysisBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 24px',
    backgroundColor: 'var(--color-primary)',
    color: 'var(--text-on-primary)',
    fontWeight: 600,
    fontSize: '14px',
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--shadow-xs)',
    border: 'none',
    cursor: 'pointer',
  },
  btnDisabled: {
    opacity: 0.7,
    cursor: 'not-allowed',
  },
  spinnerDot: {
    width: '14px',
    height: '14px',
    border: '2px solid #FFFFFF',
    borderTopColor: 'transparent',
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'spin 1s linear infinite',
  },
  analysisSuccessBanner: {
    padding: '16px 20px',
    backgroundColor: 'var(--color-success-bg)',
    border: '1px solid #A7F3D0',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  readyBannerHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  successBadge: {
    fontSize: '13px',
    fontWeight: 700,
    color: 'var(--color-success)',
  },
  readyBannerText: {
    fontSize: '13.5px',
    color: 'var(--text-main)',
    lineHeight: '1.5',
  },
  resultMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    color: 'var(--text-muted)',
    flexWrap: 'wrap',
    paddingTop: '4px',
    borderTop: '1px solid rgba(16, 185, 129, 0.2)',
  },
};

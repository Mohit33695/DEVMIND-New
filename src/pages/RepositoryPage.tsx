import React, { useRef } from 'react';
import { UploadCard } from '@/components/repository/UploadCard';
import { SecurityPanel } from '@/components/repository/SecurityPanel';
import { ExistingRepositoriesSection } from '@/components/repository/ExistingRepositoriesSection';
import { AnalysisPipelineSection } from '@/components/repository/AnalysisPipelineSection';

export const RepositoryPage: React.FC = () => {
  const uploadSectionRef = useRef<HTMLDivElement | null>(null);

  const handleScrollToUpload = () => {
    uploadSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div style={styles.pageContainer}>
      {/* 1. Page Heading */}
      <div style={styles.pageHeader}>
        <div style={styles.engineLabel}>DevMind Code Engine</div>
        <h1 style={styles.heading}>Add a repository</h1>
        <p style={styles.subheading}>
          Upload a compressed source archive (.zip) to index your codebase into DevMind software intelligence memory.
        </p>
      </div>

      {/* 2. Repository Upload Card */}
      <div ref={uploadSectionRef}>
        <UploadCard />
      </div>

      {/* 3. Security Information Panel */}
      <SecurityPanel />

      {/* 4. Existing Repositories Section (Empty State) */}
      <ExistingRepositoriesSection onAddFirstRepo={handleScrollToUpload} />

      {/* 5. How Repository Analysis Works Pipeline */}
      <AnalysisPipelineSection />
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  pageContainer: {
    maxWidth: '960px',
    margin: '0 auto',
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  pageHeader: {
    marginBottom: '28px',
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
};

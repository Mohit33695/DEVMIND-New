import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DocumentationPanel } from '@/components/repository/DocumentationPanel';
import { getActiveRepositoryId, REPO_CHANGED_EVENT } from '@/utils/repositorySession';

export const DocumentationPage: React.FC = () => {
  const [repoId, setRepoId] = useState<string | null>(() => getActiveRepositoryId());
  const navigate = useNavigate();

  useEffect(() => {
    const handleRepoChanged = () => {
      setRepoId(getActiveRepositoryId());
    };

    window.addEventListener(REPO_CHANGED_EVENT, handleRepoChanged);
    window.addEventListener('storage', handleRepoChanged);

    return () => {
      window.removeEventListener(REPO_CHANGED_EVENT, handleRepoChanged);
      window.removeEventListener('storage', handleRepoChanged);
    };
  }, []);

  const handleSelectFile = (filePath: string) => {
    navigate(`/repository?file=${encodeURIComponent(filePath)}`);
  };

  return (
    <div style={styles.pageContainer}>
      <DocumentationPanel
        repoId={repoId || undefined}
        onSelectFile={handleSelectFile}
      />
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
};


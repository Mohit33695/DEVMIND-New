import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TestingPanel } from '@/components/repository/TestingPanel';

export const TestingPage: React.FC = () => {
  const [repoId, setRepoId] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const activeId = sessionStorage.getItem('devmind_active_repo_id');
    setRepoId(activeId);
  }, []);

  const handleSelectFile = (filePath: string) => {
    navigate(`/repository?file=${encodeURIComponent(filePath)}`);
  };

  return (
    <div style={styles.pageContainer}>
      <TestingPanel
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

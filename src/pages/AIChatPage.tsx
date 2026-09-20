import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { RepositoryChat } from '@/components/repository/RepositoryChat';
import { RagStatusPanel } from '@/components/repository/RagStatusPanel';

type ActiveTab = 'chat' | 'rag';

export const AIChatPage: React.FC = () => {
  const [repoId, setRepoId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('chat');
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
      {/* Top Navigation Tabs */}
      <div style={styles.tabBar}>
        <button
          style={activeTab === 'chat' ? styles.tabActive : styles.tabInactive}
          onClick={() => setActiveTab('chat')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          Repository AI Chat
        </button>

        <button
          style={activeTab === 'rag' ? styles.tabActive : styles.tabInactive}
          onClick={() => setActiveTab('rag')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
            <polygon points="12 2 2 7 12 12 22 7 12 2" />
            <polyline points="2 17 12 22 22 17" />
            <polyline points="2 12 12 17 22 12" />
          </svg>
          RAG Status & Vector Retrieval
        </button>
      </div>

      {/* Main View Area */}
      <div style={styles.contentArea}>
        {activeTab === 'chat' ? (
          <RepositoryChat
            repoId={repoId || undefined}
            onSelectFile={handleSelectFile}
          />
        ) : (
          <RagStatusPanel
            repoId={repoId || undefined}
            onSelectFile={handleSelectFile}
          />
        )}
      </div>
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
    gap: '16px',
  },
  tabBar: {
    display: 'flex',
    gap: '8px',
    borderBottom: '1px solid #1e293b',
    paddingBottom: '4px',
  },
  tabActive: {
    padding: '10px 18px',
    backgroundColor: '#1e293b',
    color: '#38bdf8',
    border: '1px solid #334155',
    borderBottom: '2px solid #38bdf8',
    borderRadius: '8px 8px 0 0',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
  },
  tabInactive: {
    padding: '10px 18px',
    backgroundColor: 'transparent',
    color: '#94a3b8',
    border: 'none',
    borderRadius: '8px 8px 0 0',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
  },
  contentArea: {
    width: '100%',
  },
};

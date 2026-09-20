import React, { useState, useEffect, useRef } from 'react';
import {
  fetchRepositoryIndexStatus,
  indexRepositoryRAG,
  sendRepositoryChatMessage,
} from '@/api/client';
import type {
  ChatMessage,
  RepositoryIndexStatus,
  RepositoryChatResponse,
  SourceReference,
} from '@/types/repository';

interface RepositoryChatProps {
  repoId?: string;
  onSelectFile?: (path: string) => void;
}

interface ChatThreadItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceReference[];
  provider?: string;
  timestamp: string;
}

export const RepositoryChat: React.FC<RepositoryChatProps> = ({
  repoId,
  onSelectFile,
}) => {
  const [statusData, setStatusData] = useState<RepositoryIndexStatus | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState<boolean>(false);
  const [isIndexing, setIsIndexing] = useState<boolean>(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Chat conversation state
  const [messages, setMessages] = useState<ChatThreadItem[]>([]);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [topK, setTopK] = useState<number>(5);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSubmitting]);

  // Fetch index status when repoId changes
  useEffect(() => {
    if (!repoId) {
      setStatusData(null);
      setStatusError(null);
      setMessages([]);
      return;
    }

    let isMounted = true;
    setIsLoadingStatus(true);
    setStatusError(null);

    fetchRepositoryIndexStatus(repoId)
      .then((res) => {
        if (isMounted) {
          setStatusData(res);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg =
            err instanceof Error ? err.message : 'Failed to fetch index status.';
          setStatusError(msg);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingStatus(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [repoId]);

  const handleIndexRepository = () => {
    if (!repoId) return;

    setIsIndexing(true);
    setStatusError(null);

    indexRepositoryRAG(repoId)
      .then((res) => {
        setStatusData(res);
      })
      .catch((err: unknown) => {
        const msg =
          err instanceof Error ? err.message : 'Failed to index repository.';
        setStatusError(msg);
      })
      .finally(() => {
        setIsIndexing(false);
      });
  };

  const handleSendMessage = (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    const trimmedMsg = inputMessage.trim();
    if (!repoId || !trimmedMsg || isSubmitting) return;

    const userItem: ChatThreadItem = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmedMsg,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userItem]);
    setInputMessage('');
    setIsSubmitting(true);
    setChatError(null);

    // Build ChatMessage array for API history
    const historyPayload: ChatMessage[] = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    sendRepositoryChatMessage(repoId, trimmedMsg, historyPayload, topK, 0.0)
      .then((res: RepositoryChatResponse) => {
        const assistantItem: ChatThreadItem = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          provider: res.provider,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, assistantItem]);
      })
      .catch((err: unknown) => {
        const msg =
          err instanceof Error ? err.message : 'Failed to generate AI response.';
        setChatError(msg);
      })
      .finally(() => {
        setIsSubmitting(false);
      });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handlePresetQuestion = (q: string) => {
    setInputMessage(q);
  };

  // 1. Empty State (No Active Repository)
  if (!repoId) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyPromptBox}>
          <div style={styles.emptyIconCircle}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h3 style={styles.emptyPromptTitle}>No Active Repository Selected</h3>
          <p style={styles.emptyPromptSubtext}>
            Upload a repository archive on the Scanner page to enable grounded Repository AI Chat.
          </p>
        </div>
      </div>
    );
  }

  // 2. Loading Index Status State
  if (isLoadingStatus && !statusData) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingBox}>
          <div style={styles.spinner} />
          <p style={styles.loadingText}>Checking repository vector index status...</p>
        </div>
      </div>
    );
  }

  const isIndexed = statusData?.status === 'indexed';

  return (
    <div style={styles.container}>
      {/* Header Bar */}
      <div style={styles.headerBar}>
        <div>
          <h2 style={styles.headerTitle}>Repository AI Chat</h2>
          <p style={styles.headerSubtitle}>
            Grounded code intelligence assistant powered by repository RAG vector context
          </p>
        </div>
        <div style={styles.headerBadges}>
          <span
            style={
              isIndexed
                ? styles.badgeIndexed
                : statusData?.status === 'indexing'
                ? styles.badgeIndexing
                : statusData?.status === 'failed'
                ? styles.badgeFailed
                : styles.badgeNotIndexed
            }
          >
            {statusData?.status || 'not_indexed'}
          </span>
          <span style={styles.badgeProvider}>
            {statusData?.embedding_provider || 'MockLLMProvider (Development/Test Mode)'}
          </span>
        </div>
      </div>

      {/* Index Warning Banner if Not Indexed */}
      {!isIndexed && (
        <div style={styles.indexBanner}>
          <div style={styles.indexBannerText}>
            <strong>Indexing Required:</strong> This repository must be indexed into RAG vector storage before starting AI Chat.
          </div>
          <button
            style={isIndexing ? styles.btnDisabled : styles.btnPrimarySm}
            onClick={handleIndexRepository}
            disabled={isIndexing}
          >
            {isIndexing ? 'Indexing...' : 'Index Repository Now'}
          </button>
        </div>
      )}

      {statusError && <div style={styles.errorBanner}>{statusError}</div>}

      {/* Chat Thread Window */}
      <div style={styles.chatWindow}>
        {messages.length === 0 ? (
          <div style={styles.threadEmptyBox}>
            <div style={styles.aiSparkleIcon}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
            </div>
            <h3 style={styles.threadEmptyTitle}>Ask Questions About This Codebase</h3>
            <p style={styles.threadEmptySubtext}>
              DevMind AI analyzes indexed repository functions, classes, dependencies, and files to provide grounded explanations with line-level source references.
            </p>

            <div style={styles.presetsGroup}>
              <button
                style={styles.presetChip}
                onClick={() => handlePresetQuestion('How is authentication implemented in this repository?')}
              >
                &quot;How is authentication implemented in this repository?&quot;
              </button>
              <button
                style={styles.presetChip}
                onClick={() => handlePresetQuestion('Where is file storage or file reading handled?')}
              >
                &quot;Where is file storage or file reading handled?&quot;
              </button>
              <button
                style={styles.presetChip}
                onClick={() => handlePresetQuestion('What are the main security controls in this project?')}
              >
                &quot;What are the main security controls in this project?&quot;
              </button>
            </div>
          </div>
        ) : (
          <div style={styles.messagesList}>
            {messages.map((item) => (
              <div
                key={item.id}
                style={item.role === 'user' ? styles.userRow : styles.assistantRow}
              >
                <div style={item.role === 'user' ? styles.userBubble : styles.assistantBubble}>
                  <div style={styles.bubbleHeader}>
                    <span style={styles.bubbleRole}>
                      {item.role === 'user' ? 'You' : 'DevMind AI'}
                    </span>
                    <span style={styles.bubbleTime}>{item.timestamp}</span>
                  </div>

                  <div style={styles.bubbleContent}>{item.content}</div>

                  {/* Render Source References if present */}
                  {item.sources && item.sources.length > 0 && (
                    <div style={styles.sourcesContainer}>
                      <div style={styles.sourcesHeader}>Verified Source References:</div>
                      <div style={styles.sourcesGrid}>
                        {item.sources.map((src, sIdx) => (
                          <div
                            key={sIdx}
                            style={styles.sourceCard}
                            onClick={() => onSelectFile && onSelectFile(src.file_path)}
                            title="Click to view file in Repository Explorer"
                          >
                            <div style={styles.sourceFileRow}>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                                <polyline points="13 2 13 9 20 9" />
                              </svg>
                              <span style={styles.sourceFilePath}>{src.file_path}</span>
                            </div>
                            <div style={styles.sourceMetaRow}>
                              <span style={styles.sourceLines}>
                                Lines {src.start_line} - {src.end_line}
                              </span>
                              {src.symbol_name && (
                                <span style={styles.sourceSymbolTag}>{src.symbol_name}</span>
                              )}
                              <span style={styles.sourceScore}>
                                {(src.relevance_score * 100).toFixed(0)}% Match
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isSubmitting && (
              <div style={styles.assistantRow}>
                <div style={styles.assistantBubble}>
                  <div style={styles.typingIndicator}>
                    <div style={styles.typingDot} />
                    <div style={styles.typingDot} />
                    <div style={styles.typingDot} />
                    <span style={styles.typingText}>Retrieving RAG vectors & generating response...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {chatError && (
        <div style={styles.errorBoxInline}>
          <p style={styles.errorSubtext}>{chatError}</p>
        </div>
      )}

      {/* Composer Input Form */}
      <form onSubmit={handleSendMessage} style={styles.composerForm}>
        <textarea
          style={styles.composerTextarea}
          placeholder={
            isIndexed
              ? "Ask a question about this repository (e.g. 'Explain how error handling is structured')..."
              : "Repository index required to enable AI Chat..."
          }
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!isIndexed || isSubmitting}
          rows={2}
        />
        <div style={styles.composerControls}>
          <div style={styles.selectGroup}>
            <label style={styles.selectLabel}>Top K:</label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              style={styles.selectInput}
              disabled={!isIndexed || isSubmitting}
            >
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
            </select>
          </div>

          <button
            type="submit"
            style={!isIndexed || isSubmitting || !inputMessage.trim() ? styles.btnDisabled : styles.btnSend}
            disabled={!isIndexed || isSubmitting || !inputMessage.trim()}
          >
            {isSubmitting ? 'Thinking...' : 'Send Query'}
          </button>
        </div>
      </form>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    padding: '24px',
    backgroundColor: '#0f172a',
    borderRadius: '12px',
    color: '#f8fafc',
    border: '1px solid #1e293b',
    minHeight: '650px',
  },
  headerBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    borderBottom: '1px solid #1e293b',
    paddingBottom: '16px',
  },
  headerTitle: {
    fontSize: '22px',
    fontWeight: '700',
    color: '#f8fafc',
    margin: 0,
  },
  headerSubtitle: {
    fontSize: '13px',
    color: '#94a3b8',
    margin: '4px 0 0 0',
  },
  headerBadges: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  },
  badgeIndexed: {
    padding: '4px 10px',
    backgroundColor: '#064e3b',
    color: '#34d399',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  badgeIndexing: {
    padding: '4px 10px',
    backgroundColor: '#075985',
    color: '#38bdf8',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  badgeNotIndexed: {
    padding: '4px 10px',
    backgroundColor: '#334155',
    color: '#94a3b8',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  badgeFailed: {
    padding: '4px 10px',
    backgroundColor: '#7f1d1d',
    color: '#fca5a5',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  badgeProvider: {
    padding: '4px 10px',
    backgroundColor: '#3b0764',
    color: '#d8b4fe',
    borderRadius: '16px',
    fontSize: '12px',
    fontWeight: '600',
    border: '1px solid #7e22ce',
  },
  indexBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#451a03',
    border: '1px solid #b45309',
    borderRadius: '8px',
    padding: '12px 16px',
    color: '#fde68a',
    fontSize: '13px',
  },
  indexBannerText: {
    flex: 1,
  },
  btnPrimarySm: {
    padding: '6px 14px',
    backgroundColor: '#d97706',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  errorBanner: {
    padding: '12px',
    backgroundColor: '#7f1d1d',
    color: '#fca5a5',
    borderRadius: '8px',
    fontSize: '13px',
  },
  chatWindow: {
    flex: 1,
    minHeight: '400px',
    maxHeight: '520px',
    overflowY: 'auto',
    backgroundColor: '#1e293b',
    borderRadius: '8px',
    border: '1px solid #334155',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
  },
  threadEmptyBox: {
    margin: 'auto',
    textAlign: 'center',
    maxWidth: '520px',
    padding: '24px 0',
  },
  aiSparkleIcon: {
    width: '56px',
    height: '56px',
    borderRadius: '50%',
    backgroundColor: '#3b0764',
    color: '#c084fc',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px auto',
    border: '1px solid #7e22ce',
  },
  threadEmptyTitle: {
    fontSize: '18px',
    fontWeight: '700',
    color: '#f8fafc',
    margin: '0 0 8px 0',
  },
  threadEmptySubtext: {
    fontSize: '13px',
    color: '#94a3b8',
    margin: '0 0 20px 0',
    lineHeight: '1.5',
  },
  presetsGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  presetChip: {
    padding: '10px 14px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#38bdf8',
    fontSize: '13px',
    textAlign: 'left',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  messagesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  userRow: {
    display: 'flex',
    justifyContent: 'flex-end',
  },
  assistantRow: {
    display: 'flex',
    justifyContent: 'flex-start',
  },
  userBubble: {
    maxWidth: '80%',
    backgroundColor: '#0284c7',
    color: '#ffffff',
    borderRadius: '12px 12px 2px 12px',
    padding: '12px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  assistantBubble: {
    maxWidth: '85%',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    borderRadius: '12px 12px 12px 2px',
    padding: '16px',
    border: '1px solid #334155',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  bubbleHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
  },
  bubbleRole: {
    fontSize: '12px',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    opacity: 0.9,
  },
  bubbleTime: {
    fontSize: '11px',
    opacity: 0.7,
  },
  bubbleContent: {
    fontSize: '14px',
    lineHeight: '1.6',
    whiteSpace: 'pre-wrap',
  },
  sourcesContainer: {
    borderTop: '1px solid #1e293b',
    paddingTop: '12px',
    marginTop: '4px',
  },
  sourcesHeader: {
    fontSize: '12px',
    fontWeight: '700',
    color: '#38bdf8',
    marginBottom: '8px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  sourcesGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  sourceCard: {
    backgroundColor: '#1e293b',
    borderRadius: '6px',
    padding: '8px 12px',
    border: '1px solid #334155',
    cursor: 'pointer',
    transition: 'all 0.15s ease-in-out',
  },
  sourceFileRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    color: '#38bdf8',
  },
  sourceFilePath: {
    fontSize: '12px',
    fontFamily: 'monospace',
    fontWeight: '600',
    textDecoration: 'underline',
  },
  sourceMetaRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    marginTop: '4px',
  },
  sourceLines: {
    fontSize: '11px',
    color: '#94a3b8',
    fontFamily: 'monospace',
  },
  sourceSymbolTag: {
    padding: '1px 6px',
    backgroundColor: '#312e81',
    color: '#a5b4fc',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: '600',
  },
  sourceScore: {
    padding: '1px 6px',
    backgroundColor: '#064e3b',
    color: '#34d399',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: '700',
  },
  typingIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 0',
  },
  typingDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: '#38bdf8',
    animation: 'pulse 1.5s infinite ease-in-out',
  },
  typingText: {
    fontSize: '13px',
    color: '#94a3b8',
  },
  composerForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    backgroundColor: '#1e293b',
    padding: '14px',
    borderRadius: '8px',
    border: '1px solid #334155',
  },
  composerTextarea: {
    width: '100%',
    padding: '10px 12px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#f8fafc',
    fontSize: '13px',
    fontFamily: 'inherit',
    resize: 'none',
    outline: 'none',
    boxSizing: 'border-box',
  },
  composerControls: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  selectGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  selectLabel: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  selectInput: {
    padding: '6px 8px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#f8fafc',
    fontSize: '12px',
  },
  btnSend: {
    padding: '8px 20px',
    backgroundColor: '#7e22ce',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  btnDisabled: {
    padding: '8px 20px',
    backgroundColor: '#334155',
    color: '#94a3b8',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    cursor: 'not-allowed',
  },
  emptyPromptBox: {
    padding: '48px 24px',
    textAlign: 'center',
    backgroundColor: '#1e293b',
    borderRadius: '8px',
    border: '1px solid #334155',
    margin: 'auto 0',
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
    margin: 'auto 0',
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
  errorBoxInline: {
    padding: '10px 14px',
    backgroundColor: '#7f1d1d',
    borderRadius: '6px',
  },
  errorSubtext: {
    color: '#fecaca',
    fontSize: '13px',
    margin: 0,
  },
};

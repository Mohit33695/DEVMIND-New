import React, { useState, useEffect } from 'react';
import { fetchHealthCheck } from '@/api/client';

type ConnectionStatus = 'checking' | 'connected' | 'offline';

export const BackendStatusBadge: React.FC = () => {
  const [status, setStatus] = useState<ConnectionStatus>('checking');
  const [serviceName, setServiceName] = useState<string>('');

  const checkStatus = async () => {
    setStatus('checking');
    try {
      const data = await fetchHealthCheck();
      if (data.status === 'ok') {
        setStatus('connected');
        setServiceName(data.service);
      } else {
        setStatus('offline');
      }
    } catch {
      setStatus('offline');
    }
  };

  useEffect(() => {
    checkStatus();
    // Periodically re-check health status every 15 seconds
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      role="status"
      aria-live="polite"
      title={
        status === 'connected'
          ? `${serviceName} (127.0.0.1:8000/api/health)`
          : status === 'offline'
          ? 'FastAPI server unreachable (127.0.0.1:8000)'
          : 'Connecting to FastAPI backend...'
      }
      style={styles.badge}
      onClick={checkStatus}
    >
      <span
        style={{
          ...styles.dot,
          ...(status === 'connected' ? styles.dotConnected : {}),
          ...(status === 'offline' ? styles.dotOffline : {}),
          ...(status === 'checking' ? styles.dotChecking : {}),
        }}
      />
      <span style={styles.text}>
        {status === 'checking' && 'Checking backend...'}
        {status === 'connected' && 'Backend Connected'}
        {status === 'offline' && 'Backend Offline'}
      </span>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-subtle)',
    padding: '4px 10px',
    borderRadius: 'var(--radius-full)',
    border: '1px solid var(--border-subtle)',
    cursor: 'pointer',
    userSelect: 'none',
  },
  dot: {
    width: '6.5px',
    height: '6.5px',
    borderRadius: '50%',
    transition: 'background-color var(--transition-fast)',
  },
  dotConnected: {
    backgroundColor: 'var(--color-success)',
  },
  dotOffline: {
    backgroundColor: 'var(--color-error)',
  },
  dotChecking: {
    backgroundColor: 'var(--text-subtle)',
    opacity: 0.6,
  },
  text: {
    lineHeight: '1',
  },
};

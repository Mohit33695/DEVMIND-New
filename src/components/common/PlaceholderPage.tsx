import React from 'react';

interface PlaceholderPageProps {
  title: string;
  category: 'Workspace' | 'Intelligence' | 'Knowledge' | 'System';
  description: string;
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({
  title,
  category,
  description,
}) => {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.headerRow}>
          <span style={styles.categoryBadge}>{category}</span>
          <span style={styles.comingNextBadge}>Coming next</span>
        </div>

        <h1 style={styles.title}>{title}</h1>
        <p style={styles.description}>{description}</p>

        <div style={styles.statusBox}>
          <div style={styles.statusHeader}>
            <span style={styles.statusDot}></span>
            <span style={styles.statusTitle}>Module Registered</span>
          </div>
          <p style={styles.statusText}>
            This module route is wired into the DevMind application shell. Screen implementation will follow in subsequent development phases.
          </p>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '720px',
    margin: '16px auto',
    width: '100%',
  },
  card: {
    backgroundColor: 'var(--bg-surface)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    padding: '36px',
    boxShadow: 'var(--shadow-sm)',
  },
  headerRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '16px',
  },
  categoryBadge: {
    fontSize: '11px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-app)',
    padding: '3px 8px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-subtle)',
  },
  comingNextBadge: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--color-primary)',
    backgroundColor: 'var(--color-primary-light)',
    padding: '3px 10px',
    borderRadius: 'var(--radius-full)',
  },
  title: {
    fontSize: '24px',
    fontWeight: 700,
    color: 'var(--text-main)',
    marginBottom: '10px',
  },
  description: {
    fontSize: '14.5px',
    color: 'var(--text-muted)',
    lineHeight: '1.6',
    marginBottom: '28px',
  },
  statusBox: {
    backgroundColor: 'var(--bg-app)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-subtle)',
    padding: '16px 20px',
  },
  statusHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: 'var(--color-primary)',
  },
  statusTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-main)',
  },
  statusText: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    lineHeight: '1.5',
  },
};

import React from 'react';

export const SecurityPanel: React.FC = () => {
  const securityItems = [
    {
      title: 'Isolated Source Storage',
      description: 'Uploaded source archives will be processed in temporary isolated storage.',
    },
    {
      title: 'Secret Non-Persistence',
      description: 'Secret detection and non-persistence protections will be enforced by the backend.',
    },
    {
      title: 'Path-Traversal Protection',
      description: 'ZIP path-traversal protection will be applied during extraction.',
    },
  ];

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerTitleRow}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--color-primary)' }}>
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <h4 style={styles.title}>Intended Security Architecture</h4>
        </div>
        <span style={styles.subtext}>Pipeline Security Specifications</span>
      </div>

      <div style={styles.grid}>
        {securityItems.map((item, idx) => (
          <div key={idx} style={styles.itemCard}>
            <div style={styles.itemDot} />
            <div style={styles.itemContent}>
              <span style={styles.itemTitle}>{item.title}</span>
              <p style={styles.itemDesc}>{item.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    padding: '24px',
    boxShadow: 'var(--shadow-xs)',
    marginTop: '24px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '16px',
    paddingBottom: '12px',
    borderBottom: '1px solid var(--border-subtle)',
    flexWrap: 'wrap',
    gap: '8px',
  },
  headerTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  title: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-main)',
  },
  subtext: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontWeight: 500,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '16px',
  },
  itemCard: {
    display: 'flex',
    gap: '12px',
    padding: '12px 14px',
    backgroundColor: 'var(--bg-app)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-subtle)',
  },
  itemDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: 'var(--color-primary)',
    marginTop: '6px',
    flexShrink: 0,
  },
  itemContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  itemTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-main)',
  },
  itemDesc: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    lineHeight: '1.4',
  },
};

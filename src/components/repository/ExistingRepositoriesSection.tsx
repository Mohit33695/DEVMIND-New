import React from 'react';

interface ExistingRepositoriesSectionProps {
  onAddFirstRepo: () => void;
}

export const ExistingRepositoriesSection: React.FC<ExistingRepositoriesSectionProps> = ({
  onAddFirstRepo,
}) => {
  return (
    <div style={styles.container}>
      <div style={styles.sectionHeader}>
        <h3 style={styles.sectionTitle}>Existing Repositories</h3>
        <span style={styles.countBadge}>0 Repositories</span>
      </div>

      <div style={styles.emptyStateCard}>
        <div style={styles.iconCircle}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
        </div>

        <h4 style={styles.emptyTitle}>No repositories yet</h4>
        <p style={styles.emptySubtext}>Your analyzed repositories will appear here once connected.</p>

        <button style={styles.addFirstBtn} onClick={onAddFirstRepo}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Add your first repository
        </button>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginTop: '40px',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '16px',
  },
  sectionTitle: {
    fontSize: '16px',
    fontWeight: 700,
    color: 'var(--text-main)',
  },
  countBadge: {
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-subtle)',
    padding: '2px 10px',
    borderRadius: 'var(--radius-full)',
    border: '1px solid var(--border-subtle)',
  },
  emptyStateCard: {
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    padding: '48px 24px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    boxShadow: 'var(--shadow-xs)',
  },
  iconCircle: {
    width: '48px',
    height: '48px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--bg-app)',
    color: 'var(--text-subtle)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '14px',
    border: '1px solid var(--border-subtle)',
  },
  emptyTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--text-main)',
    marginBottom: '6px',
  },
  emptySubtext: {
    fontSize: '13.5px',
    color: 'var(--text-muted)',
    marginBottom: '20px',
  },
  addFirstBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 16px',
    backgroundColor: 'var(--color-primary-light)',
    color: 'var(--color-primary)',
    fontWeight: 600,
    fontSize: '13px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-subtle)',
    cursor: 'pointer',
    transition: 'background-color var(--transition-fast)',
  },
};

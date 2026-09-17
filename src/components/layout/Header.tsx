import React from 'react';
import { useLocation } from 'react-router-dom';
import { BackendStatusBadge } from './BackendStatusBadge';

interface HeaderProps {
  onToggleMobileSidebar: () => void;
}

const routeTitleMap: Record<string, string> = {
  '/': 'Overview',
  '/repository': 'Repository Scanner',
  '/ai-chat': 'AI Chat Assistant',
  '/architecture': 'Architecture Intelligence',
  '/security': 'Security Scanner',
  '/code-quality': 'Code Quality & Linting',
  '/testing': 'Test Coverage & Suite',
  '/dependencies': 'Dependency Graph',
  '/documentation': 'Documentation Generator',
  '/git-history': 'Git History & Insights',
  '/settings': 'Platform Settings',
  '/help': 'Help & API Docs',
};

export const Header: React.FC<HeaderProps> = ({ onToggleMobileSidebar }) => {
  const location = useLocation();
  const currentTitle = routeTitleMap[location.pathname] || 'Overview';

  return (
    <header style={styles.header}>
      {/* Mobile Toggle & Breadcrumb */}
      <div style={styles.leftSection}>
        <button
          className="mobile-menu-btn"
          style={styles.mobileMenuBtn}
          onClick={onToggleMobileSidebar}
          aria-label="Toggle navigation menu"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        <div style={styles.breadcrumb}>
          <span style={styles.repoCrumb}>devmind-ai/core</span>
          <span style={styles.crumbSeparator}>/</span>
          <span style={styles.activeCrumb}>{currentTitle}</span>
        </div>
      </div>

      {/* Center Search Field */}
      <div style={styles.centerSection}>
        <div style={styles.searchBox}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={styles.searchIcon}>
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Search codebase, symbols, architecture..."
            style={styles.searchInput}
            readOnly
          />
          <span style={styles.searchShortcut}>⌘K</span>
        </div>
      </div>

      {/* Right Controls Section */}
      <div style={styles.rightSection}>
        {/* Backend Connection Status */}
        <BackendStatusBadge />

        {/* Re-analyze Button */}
        <button style={styles.reanalyzeBtn} title="Trigger codebase re-analysis">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
          </svg>
          <span style={styles.btnLabel}>Re-analyze</span>
        </button>

        {/* Notification Icon */}
        <button style={styles.iconBtn} aria-label="Notifications">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span style={styles.notificationDot} />
        </button>

        {/* Profile Control */}
        <div style={styles.profileControl}>
          <div style={styles.headerAvatar}>MG</div>
        </div>
      </div>
    </header>
  );
};

const styles: Record<string, React.CSSProperties> = {
  header: {
    height: 'var(--header-height)',
    backgroundColor: 'var(--bg-surface)',
    borderBottom: '1px solid var(--border-default)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 24px',
    position: 'sticky',
    top: 0,
    zIndex: 40,
    gap: '16px',
  },
  leftSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    minWidth: '220px',
  },
  mobileMenuBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '6px',
    color: 'var(--text-muted)',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-subtle)',
    cursor: 'pointer',
  },
  breadcrumb: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13.5px',
    fontWeight: 500,
  },
  repoCrumb: {
    color: 'var(--text-muted)',
  },
  crumbSeparator: {
    color: 'var(--text-subtle)',
  },
  activeCrumb: {
    color: 'var(--text-main)',
    fontWeight: 600,
  },
  centerSection: {
    flex: 1,
    maxWidth: '480px',
  },
  searchBox: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    width: '100%',
  },
  searchIcon: {
    position: 'absolute',
    left: '12px',
    color: 'var(--text-subtle)',
    pointerEvents: 'none',
  },
  searchInput: {
    width: '100%',
    padding: '7px 36px 7px 34px',
    backgroundColor: 'var(--bg-app)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '13px',
    color: 'var(--text-main)',
    outline: 'none',
  },
  searchShortcut: {
    position: 'absolute',
    right: '10px',
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-subtle)',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    padding: '1px 5px',
    borderRadius: 'var(--radius-sm)',
    pointerEvents: 'none',
  },
  rightSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
  },
  analysisStatus: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-subtle)',
    padding: '4px 10px',
    borderRadius: 'var(--radius-full)',
    border: '1px solid var(--border-subtle)',
  },
  statusDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: 'var(--color-success)',
  },
  statusText: {
    fontWeight: 500,
  },
  reanalyzeBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-main)',
    fontSize: '12.5px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'background-color var(--transition-fast)',
  },
  btnLabel: {
    lineHeight: '1',
  },
  iconBtn: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '6px',
    color: 'var(--text-muted)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  notificationDot: {
    position: 'absolute',
    top: '5px',
    right: '5px',
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    backgroundColor: 'var(--color-primary)',
    border: '1.5px solid var(--bg-surface)',
  },
  profileControl: {
    cursor: 'pointer',
  },
  headerAvatar: {
    width: '30px',
    height: '30px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--color-primary-light)',
    color: 'var(--color-primary)',
    fontWeight: 700,
    fontSize: '11px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid var(--border-default)',
  },
};

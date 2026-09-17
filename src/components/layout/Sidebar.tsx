import React from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';

interface SidebarProps {
  isOpenOnMobile: boolean;
  onCloseMobile: () => void;
}

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpenOnMobile, onCloseMobile }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleAddRepository = () => {
    navigate('/repository');
    if (isOpenOnMobile) onCloseMobile();
  };

  const navSections: NavSection[] = [
    {
      title: 'Workspace',
      items: [
        {
          label: 'Overview',
          path: '/',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
            </svg>
          ),
        },
        {
          label: 'Repository',
          path: '/repository',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
          ),
        },
        {
          label: 'AI Chat',
          path: '/ai-chat',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          ),
        },
        {
          label: 'Architecture',
          path: '/architecture',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          ),
        },
      ],
    },
    {
      title: 'Intelligence',
      items: [
        {
          label: 'Security',
          path: '/security',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          ),
        },
        {
          label: 'Code Quality',
          path: '/code-quality',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          ),
        },
        {
          label: 'Testing',
          path: '/testing',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
            </svg>
          ),
        },
        {
          label: 'Dependencies',
          path: '/dependencies',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="16.5" y1="9.4" x2="7.5" y2="4.2" />
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
              <line x1="12" y1="22.08" x2="12" y2="12" />
            </svg>
          ),
        },
      ],
    },
    {
      title: 'Knowledge',
      items: [
        {
          label: 'Documentation',
          path: '/documentation',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          ),
        },
        {
          label: 'Git History',
          path: '/git-history',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <line x1="3" y1="12" x2="9" y2="12" />
              <line x1="15" y1="12" x2="21" y2="12" />
            </svg>
          ),
        },
      ],
    },
    {
      title: 'System',
      items: [
        {
          label: 'Settings',
          path: '/settings',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          ),
        },
        {
          label: 'Help & API Docs',
          path: '/help',
          icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          ),
        },
      ],
    },
  ];

  return (
    <>
      {/* Mobile overlay backdrop */}
      {isOpenOnMobile && <div style={styles.mobileBackdrop} onClick={onCloseMobile} />}

      <aside style={{ ...styles.sidebar, ...(isOpenOnMobile ? styles.sidebarMobileOpen : {}) }}>
        {/* Sidebar Header: Logo & Brand */}
        <div style={styles.sidebarHeader}>
          <div style={styles.logoBadge}>DM</div>
          <div style={styles.brandTitleArea}>
            <span style={styles.brandName}>DevMind AI</span>
            <span style={styles.brandTagline}>Software Intelligence</span>
          </div>
        </div>

        {/* Repository Selector & Branch Bar */}
        <div style={styles.repoSelectorBox}>
          <div style={styles.repoSelectorHeader}>
            <div style={styles.repoInfo}>
              <span style={styles.repoName}>devmind-ai/core</span>
              <span style={styles.branchBadge}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="6" y1="3" x2="6" y2="15" />
                  <circle cx="18" cy="6" r="3" />
                  <circle cx="6" cy="18" r="3" />
                  <path d="M18 9a9 9 0 0 1-9 9" />
                </svg>
                main
              </span>
            </div>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>

          <button style={styles.addRepoBtn} onClick={handleAddRepository}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Add Repository
          </button>
        </div>

        {/* Navigation Sections */}
        <div style={styles.navContainer}>
          {navSections.map((section) => (
            <div key={section.title} style={styles.navSection}>
              <div style={styles.sectionTitle}>{section.title}</div>
              <div style={styles.sectionList}>
                {section.items.map((item) => {
                  const isActive = location.pathname === item.path;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => {
                        if (isOpenOnMobile) onCloseMobile();
                      }}
                      style={({ isActive: linkActive }) => ({
                        ...styles.navLink,
                        ...(linkActive ? styles.navLinkActive : {}),
                      })}
                    >
                      <span style={{ ...styles.navIcon, ...(isActive ? styles.navIconActive : {}) }}>
                        {item.icon}
                      </span>
                      <span style={styles.navLabel}>{item.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* User Profile Footer */}
        <div style={styles.profileFooter}>
          <div style={styles.avatar}>MG</div>
          <div style={styles.userInfo}>
            <span style={styles.userName}>Mohit Gaonkar</span>
            <span style={styles.userRole}>Lead Engineer</span>
          </div>
        </div>
      </aside>
    </>
  );
};

const styles: Record<string, React.CSSProperties> = {
  mobileBackdrop: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(17, 24, 39, 0.4)',
    zIndex: 45,
  },
  sidebar: {
    width: 'var(--sidebar-width)',
    height: '100vh',
    backgroundColor: 'var(--bg-sidebar)',
    borderRight: '1px solid var(--border-default)',
    display: 'flex',
    flexDirection: 'column',
    position: 'sticky',
    top: 0,
    zIndex: 50,
    transition: 'transform var(--transition-normal)',
  },
  sidebarMobileOpen: {
    position: 'fixed',
    top: 0,
    left: 0,
    bottom: 0,
    transform: 'translateX(0)',
    boxShadow: 'var(--shadow-md)',
  },
  sidebarHeader: {
    height: 'var(--header-height)',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '0 20px',
    borderBottom: '1px solid var(--border-subtle)',
  },
  logoBadge: {
    width: '32px',
    height: '32px',
    backgroundColor: 'var(--color-primary)',
    color: 'var(--text-on-primary)',
    fontWeight: 700,
    fontSize: '13px',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    letterSpacing: '0.5px',
  },
  brandTitleArea: {
    display: 'flex',
    flexDirection: 'column',
  },
  brandName: {
    fontSize: '15px',
    fontWeight: 700,
    color: 'var(--text-main)',
    lineHeight: '1.2',
  },
  brandTagline: {
    fontSize: '11px',
    fontWeight: 500,
    color: 'var(--text-muted)',
  },
  repoSelectorBox: {
    padding: '16px 16px 12px 16px',
    borderBottom: '1px solid var(--border-subtle)',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  repoSelectorHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 10px',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    color: 'var(--text-muted)',
  },
  repoInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  repoName: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-main)',
  },
  branchBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    color: 'var(--text-muted)',
    fontWeight: 500,
  },
  addRepoBtn: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    padding: '7px 12px',
    backgroundColor: 'var(--color-primary-light)',
    color: 'var(--color-primary)',
    borderRadius: 'var(--radius-md)',
    fontWeight: 600,
    fontSize: '12px',
    transition: 'background-color var(--transition-fast)',
  },
  navContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  navSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  sectionTitle: {
    fontSize: '11px',
    fontWeight: 700,
    color: 'var(--text-subtle)',
    textTransform: 'uppercase',
    letterSpacing: '0.6px',
    padding: '0 8px 6px 8px',
  },
  sectionList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  navLink: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 10px',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-muted)',
    fontSize: '13.5px',
    fontWeight: 500,
    textDecoration: 'none',
    transition: 'all var(--transition-fast)',
  },
  navLinkActive: {
    backgroundColor: 'var(--color-primary-light)',
    color: 'var(--color-primary)',
    fontWeight: 600,
  },
  navIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--text-muted)',
  },
  navIconActive: {
    color: 'var(--color-primary)',
  },
  navLabel: {
    lineHeight: '1',
  },
  profileFooter: {
    padding: '14px 16px',
    borderTop: '1px solid var(--border-subtle)',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    backgroundColor: 'var(--bg-surface)',
  },
  avatar: {
    width: '34px',
    height: '34px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--color-primary-light)',
    color: 'var(--color-primary)',
    fontWeight: 700,
    fontSize: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid var(--border-default)',
  },
  userInfo: {
    display: 'flex',
    flexDirection: 'column',
  },
  userName: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-main)',
    lineHeight: '1.2',
  },
  userRole: {
    fontSize: '11px',
    color: 'var(--text-muted)',
  },
};

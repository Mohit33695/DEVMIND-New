import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { syncRepositoriesWithBackend } from '@/utils/repositorySession';

export const MainLayout: React.FC = () => {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  useEffect(() => {
    // Initial sync with backend on app mount (survives browser restarts)
    syncRepositoriesWithBackend().catch(() => {});
  }, []);

  const toggleMobileSidebar = () => {
    setIsMobileSidebarOpen((prev) => !prev);
  };

  const closeMobileSidebar = () => {
    setIsMobileSidebarOpen(false);
  };

  return (
    <div className="app-shell">
      <Sidebar
        isOpenOnMobile={isMobileSidebarOpen}
        onCloseMobile={closeMobileSidebar}
      />
      <div className="app-main-wrapper">
        <Header onToggleMobileSidebar={toggleMobileSidebar} />
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export const MainLayout: React.FC = () => {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

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

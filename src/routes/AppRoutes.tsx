import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { OverviewPage } from '@/pages/OverviewPage';
import { RepositoryPage } from '@/pages/RepositoryPage';
import { AIChatPage } from '@/pages/AIChatPage';
import { ArchitecturePage } from '@/pages/ArchitecturePage';
import { SecurityPage } from '@/pages/SecurityPage';
import { CodeQualityPage } from '@/pages/CodeQualityPage';
import { TestingPage } from '@/pages/TestingPage';
import { DependenciesPage } from '@/pages/DependenciesPage';
import { DocumentationPage } from '@/pages/DocumentationPage';
import { GitHistoryPage } from '@/pages/GitHistoryPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { HelpPage } from '@/pages/HelpPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="repository" element={<RepositoryPage />} />
        <Route path="ai-chat" element={<AIChatPage />} />
        <Route path="architecture" element={<ArchitecturePage />} />
        <Route path="security" element={<SecurityPage />} />
        <Route path="code-quality" element={<CodeQualityPage />} />
        <Route path="testing" element={<TestingPage />} />
        <Route path="dependencies" element={<DependenciesPage />} />
        <Route path="documentation" element={<DocumentationPage />} />
        <Route path="git-history" element={<GitHistoryPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="help" element={<HelpPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
};

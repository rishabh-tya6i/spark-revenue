import React from 'react';
import { Outlet } from 'react-router-dom';
import SidebarNav from './SidebarNav';
import TopContextBar from './TopContextBar';

const AppShell: React.FC = () => {
  return (
    <div className="app-shell">
      <SidebarNav />
      <div className="main-container">
        <TopContextBar />
        <Outlet />
      </div>
    </div>
  );
};

export default AppShell;

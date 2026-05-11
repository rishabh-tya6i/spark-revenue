import React from 'react';
import { NavLink } from 'react-router-dom';
import { Layout, LineChart, Bell, Activity, Settings, Zap, Send, History } from 'lucide-react';

const SidebarNav: React.FC = () => {
  return (
    <nav className="sidebar">
      <div className="logo" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <Activity size={32} color="var(--primary)" />
        <span style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>SPARK</span>
      </div>
      
      <div style={{ flex: 1, paddingTop: '12px' }}>
        <NavLink 
          to="/overview" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Layout size={20} />
          <span>Overview</span>
        </NavLink>

        <NavLink 
          to="/operations" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Settings size={20} />
          <span>Operations</span>
        </NavLink>

        <NavLink 
          to="/execution" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Send size={20} />
          <span>Execution</span>
        </NavLink>

        <NavLink 
          to="/runs" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <History size={20} />
          <span>Runs</span>
        </NavLink>

        <NavLink 
          to="/signals" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Zap size={20} />
          <span>Signals</span>
        </NavLink>
        
        <NavLink 
          to="/backtest" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <LineChart size={20} />
          <span>Backtest</span>
        </NavLink>
        
        <NavLink 
          to="/alerts" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Bell size={20} />
          <span>Alerts</span>
        </NavLink>
      </div>

      <div style={{ padding: '20px', borderTop: '1px solid var(--border)' }}>
        <div className="text-xs text-muted text-mono">v0.1.0-alpha</div>
      </div>
    </nav>
  );
};

export default SidebarNav;

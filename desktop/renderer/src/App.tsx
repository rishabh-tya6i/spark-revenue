import React, { useState } from 'react';
import { SymbolProvider } from './context/SymbolContext';
import DashboardPage from './pages/DashboardPage';
import BacktestPage from './pages/BacktestPage';
import AlertsPage from './pages/AlertsPage';
import { Layout, LineChart, Bell, Activity } from 'lucide-react';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'backtest' | 'alerts'>('dashboard');

  return (
    <SymbolProvider>
      <div className="app-container">
        <nav className="sidebar">
          <div className="logo">
            <Activity className="logo-icon" size={32} color="#00ff88" />
            <span>Spark Revenue</span>
          </div>
          <div className="nav-items">
            <button 
              className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <Layout size={20} />
              <span>Dashboard</span>
            </button>
            <button 
              className={`nav-item ${activeTab === 'backtest' ? 'active' : ''}`}
              onClick={() => setActiveTab('backtest')}
            >
              <LineChart size={20} />
              <span>Backtest</span>
            </button>
            <button 
              className={`nav-item ${activeTab === 'alerts' ? 'active' : ''}`}
              onClick={() => setActiveTab('alerts')}
            >
              <Bell size={20} />
              <span>Alerts</span>
            </button>
          </div>
        </nav>
        <main className="content">
          {activeTab === 'dashboard' && <DashboardPage />}
          {activeTab === 'backtest' && <BacktestPage />}
          {activeTab === 'alerts' && <AlertsPage />}
        </main>
      </div>
    </SymbolProvider>
  );
};

export default App;

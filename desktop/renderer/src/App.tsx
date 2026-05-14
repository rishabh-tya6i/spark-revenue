import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { SymbolProvider } from './context/SymbolContext';
import AppShell from './components/layout/AppShell';
import OverviewPage from './pages/OverviewPage';
import OperationsPage from './pages/OperationsPage';
import ExecutionPage from './pages/ExecutionPage';
import RunsPage from './pages/RunsPage';
import DashboardPage from './pages/DashboardPage';
import BacktestPage from './pages/BacktestPage';
import AlertsPage from './pages/AlertsPage';
import SetupPage from './pages/SetupPage';

const App: React.FC = () => {
  return (
    <SymbolProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/overview" element={<OverviewPage />} />
          <Route path="/operations" element={<OperationsPage />} />
          <Route path="/setup" element={<SetupPage />} />
          <Route path="/execution" element={<ExecutionPage />} />
          <Route path="/runs" element={<RunsPage />} />
            <Route path="/signals" element={<DashboardPage />} />
            <Route path="/backtest" element={<BacktestPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/" element={<Navigate to="/overview" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </SymbolProvider>
  );
};

export default App;

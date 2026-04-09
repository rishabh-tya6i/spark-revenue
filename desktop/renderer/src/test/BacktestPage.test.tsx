import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BacktestPage from '../pages/BacktestPage';
import { SymbolProvider } from '../context/SymbolContext';
import * as backtestApi from '../api/backtestApi';

vi.mock('../api/backtestApi');

const mockBacktestResult = {
  run: {
    id: 1,
    strategy_name: 'rule_based',
    symbol: 'BTCUSDT',
    interval: '5m',
    start_ts: '2023-01-01T00:00:00Z',
    end_ts: '2023-12-31T00:00:00Z',
    initial_capital: 10000,
    final_capital: 12000,
    status: 'COMPLETED',
    created_ts: new Date().toISOString(),
  },
  metrics: {
    backtest_id: 1,
    metrics: {
      win_rate: 0.65,
      max_drawdown: 0.1,
      sharpe: 2.5,
    },
  },
};

describe('BacktestPage', () => {
  it('runs backtest and renders metrics', async () => {
    vi.mocked(backtestApi.runBacktest).mockResolvedValue(mockBacktestResult);

    render(
      <SymbolProvider>
        <BacktestPage />
      </SymbolProvider>
    );

    fireEvent.click(screen.getByText('Run Backtest'));

    await waitFor(() => {
      expect(screen.getByText('$12,000')).toBeInTheDocument();
      expect(screen.getByText('20.00%')).toBeInTheDocument();
      expect(screen.getByText('65.0%')).toBeInTheDocument();
      expect(screen.getByText('2.50')).toBeInTheDocument();
    });
  });
});

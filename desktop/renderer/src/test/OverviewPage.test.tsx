import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import OverviewPage from '../pages/OverviewPage';
import { SymbolProvider } from '../context/SymbolContext';
import * as orchestrationApi from '../api/orchestrationApi';

vi.mock('../api/orchestrationApi');

const mockState = {
  mode: 'explicit',
  interval: '5m',
  symbols: ['NIFTY', 'BANKNIFTY'],
  inference_ready_symbols: ['NIFTY'],
  execution_ready_symbols: ['NIFTY'],
  models: {
    symbols_checked: 2,
    price_model_available: ['NIFTY'],
    rl_agent_available: ['NIFTY'],
    missing_price_model: ['BANKNIFTY'],
    missing_rl_agent: ['BANKNIFTY'],
  },
  decisions: {
    symbols_checked: 2,
    has_decision: ['NIFTY'],
    actionable: ['NIFTY'],
    hold: [],
    missing: ['BANKNIFTY'],
  },
  execution_state: {
    symbols_checked: 2,
    has_orders: [],
    open_positions: [],
    no_activity: ['NIFTY', 'BANKNIFTY'],
  },
  execution_guardrails: {
    execution_enabled: true,
    allowed_actions: ['BUY', 'SELL'],
    max_symbols_per_run: 5,
  },
  execution_overrides: {
    active_symbols: [],
    actions: {},
  },
  execution_dispatch: {
    symbols_checked: 2,
    already_dispatched: [],
    not_dispatched: ['NIFTY', 'BANKNIFTY'],
  },
  execution_staleness: {
    symbols_checked: 2,
    stale_decision_symbols: [],
    stale_override_symbols: [],
    fresh_candidates: ['NIFTY'],
  },
  latest_runs: {
    train: { id: 101, run_type: 'train', status: 'COMPLETED', created_ts: new Date().toISOString() },
    inference: null,
    execution: null,
    cycle: null,
  },
};

describe('OverviewPage', () => {
  it('renders orchestration state sections', async () => {
    vi.mocked(orchestrationApi.getOperationalState).mockResolvedValue(mockState as any);

    render(
      <SymbolProvider>
        <OverviewPage />
      </SymbolProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Universe & Readiness')).toBeInTheDocument();
      expect(screen.getByText('EXPLICIT / 5m')).toBeInTheDocument();
      expect(screen.getByText('1 / 2')).toBeInTheDocument(); // Inference ready
      expect(screen.getByText('1 actionable')).toBeInTheDocument();
      
      expect(screen.getByText('Model Availability')).toBeInTheDocument();
      expect(screen.getByText('MISSING PRICE: BANKNIFTY')).toBeInTheDocument();
      
      expect(screen.getByText('Latest Orchestration Runs')).toBeInTheDocument();
      expect(screen.getByText('ID: 101')).toBeInTheDocument();
    });
  });

  it('renders loading state', async () => {
    vi.mocked(orchestrationApi.getOperationalState).mockReturnValue(new Promise(() => {}));

    render(
      <SymbolProvider>
        <OverviewPage />
      </SymbolProvider>
    );

    expect(screen.getByText('Synchronizing state...')).toBeInTheDocument();
  });
});

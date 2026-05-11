import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from '../App';

// Mock the API calls
vi.mock('../api/orchestrationApi', () => ({
  getOperationalState: vi.fn().mockResolvedValue({
    mode: 'explicit',
    interval: '5m',
    symbols: [],
    inference_ready_symbols: [],
    execution_ready_symbols: [],
    models: { price_model_available: [], rl_agent_available: [], missing_price_model: [], missing_rl_agent: [] },
    decisions: { has_decision: [], actionable: [], hold: [], missing: [] },
    execution_state: { has_orders: [], open_positions: [], no_activity: [] },
    execution_guardrails: { execution_enabled: true, allowed_actions: [], max_symbols_per_run: 5 },
    execution_overrides: { active_symbols: [], actions: {} },
    execution_dispatch: { already_dispatched: [], not_dispatched: [] },
    execution_staleness: { fresh_candidates: [] },
    latest_runs: { train: null, inference: null, execution: null, cycle: null }
  })
}));

vi.mock('../api/decisionApi', () => ({
  getLatestDecision: vi.fn().mockResolvedValue(null)
}));
vi.mock('../api/optionsApi', () => ({
  getOptionsSignal: vi.fn().mockResolvedValue(null)
}));
vi.mock('../api/sentimentApi', () => ({
  getLatestSentiment: vi.fn().mockResolvedValue([])
}));

describe('App Shell and Routing', () => {
  it('renders sidebar with new navigation items', async () => {
    render(<App />);
    
    await waitFor(() => {
      expect(screen.getByText('Universe & Readiness')).toBeInTheDocument();
    });

    expect(screen.getByText('SPARK')).toBeInTheDocument();
    expect(screen.getAllByText('Overview').length).toBeGreaterThan(0);
    expect(screen.getByText('Operations')).toBeInTheDocument();
    expect(screen.getByText('Execution')).toBeInTheDocument();
    expect(screen.getByText('Runs')).toBeInTheDocument();
    expect(screen.getByText('Signals')).toBeInTheDocument();
    expect(screen.getByText('Backtest')).toBeInTheDocument();
    expect(screen.getByText('Alerts')).toBeInTheDocument();
  });

  it('defaults to NIFTY and 5m', async () => {
    render(<App />);
    
    await waitFor(() => {
      expect(screen.getByText('Universe & Readiness')).toBeInTheDocument();
    });

    const symbolInput = screen.getByDisplayValue('NIFTY');
    const intervalSelect = screen.getByDisplayValue('5m');
    
    expect(symbolInput).toBeInTheDocument();
    expect(intervalSelect).toBeInTheDocument();
  });

  it('redirects / to /overview', async () => {
    render(<App />);
    
    await waitFor(() => {
      expect(screen.getByText('Universe & Readiness')).toBeInTheDocument();
    });
  });
});

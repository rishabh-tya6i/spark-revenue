import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ExecutionPage from '../pages/ExecutionPage';
import { SymbolProvider } from '../context/SymbolContext';
import * as orchestrationApi from '../api/orchestrationApi';

vi.mock('../api/orchestrationApi');

const mockReadiness = {
  mode: 'explicit',
  interval: '5m',
  symbols: ['NIFTY'],
  execution_ready_symbols: ['NIFTY'],
  details: [
    {
      symbol: 'NIFTY',
      decision_label: 'BUY',
      decision_score: 0.85,
      rl_action: 'BUY',
      ready: true,
      reason: 'All checks passed',
      decision_ts: new Date().toISOString(),
      decision_stale: false,
      override_active: false
    }
  ]
};

const mockGuardrails = {
  mode: 'explicit',
  interval: '5m',
  execution_ready_symbols: ['NIFTY'],
  guardrails: {
    execution_enabled: true,
    allowed_actions: ['BUY', 'SELL'],
    max_symbols_per_run: 5,
    requested_ready_symbols: ['NIFTY'],
    allowed_symbols: ['NIFTY'],
    blocked_symbols: []
  },
  guardrail_summary: {
    execution_enabled: true,
    allowed_actions: ['BUY', 'SELL'],
    max_symbols_per_run: 5,
    allowed_count: 1,
    blocked_count: 0
  }
};

const mockOverrides = [
  { id: 1, symbol: 'BANKNIFTY', interval: '5m', override_action: 'SKIP', created_ts: new Date().toISOString() }
];

const mockDispatches = [
  { id: 10, symbol: 'NIFTY', interval: '5m', source_type: 'decision', source_id: 100, dispatched_action: 'BUY', status: 'executed', created_ts: new Date().toISOString() }
];

const mockStaleness = {
  mode: 'explicit',
  interval: '5m',
  symbols: ['NIFTY'],
  details: [
    { 
      symbol: 'NIFTY', 
      decision_stale: false, 
      decision_ts: new Date().toISOString(),
      override_active: false
    }
  ],
  summary: {
    symbols_checked: 1,
    stale_decision_symbols: [],
    stale_override_symbols: [],
    fresh_candidates: ['NIFTY']
  }
};

describe('ExecutionPage', () => {
  beforeEach(() => {
    vi.mocked(orchestrationApi.getExecutionReadiness).mockResolvedValue(mockReadiness as any);
    vi.mocked(orchestrationApi.getExecutionGuardrails).mockResolvedValue(mockGuardrails as any);
    vi.mocked(orchestrationApi.getExecutionOverrides).mockResolvedValue(mockOverrides as any);
    vi.mocked(orchestrationApi.getExecutionDispatches).mockResolvedValue(mockDispatches as any);
    vi.mocked(orchestrationApi.getExecutionStaleness).mockResolvedValue(mockStaleness as any);
  });

  it('renders all management sections', async () => {
    render(
      <SymbolProvider>
        <ExecutionPage />
      </SymbolProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Execution Readiness')).toBeInTheDocument();
      expect(screen.getByText('Execution Guardrails')).toBeInTheDocument();
      expect(screen.getByText('Manual Overrides')).toBeInTheDocument();
      expect(screen.getByText('Dispatch Ledger')).toBeInTheDocument();
      expect(screen.getByText('Staleness Inspection')).toBeInTheDocument();
    });

    expect(screen.getAllByText('BUY').length).toBeGreaterThan(0);
    expect(screen.getByText('BANKNIFTY')).toBeInTheDocument();
    expect(screen.getByText('DECISION (100)')).toBeInTheDocument();
  });

  it('triggers override creation', async () => {
    vi.mocked(orchestrationApi.setExecutionOverride).mockResolvedValue({ id: 2 } as any);

    render(
      <SymbolProvider>
        <ExecutionPage />
      </SymbolProvider>
    );

    const symbolInput = screen.getByPlaceholderText('BTC-USD');
    fireEvent.change(symbolInput, { target: { value: 'ETH-USD' } });
    
    const submitButton = screen.getByLabelText('Add Override');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(orchestrationApi.setExecutionOverride).toHaveBeenCalledWith(expect.objectContaining({
        symbol: 'ETH-USD',
        override_action: 'SKIP'
      }));
    });
  });

  it('triggers override clearing', async () => {
    vi.mocked(orchestrationApi.clearExecutionOverride).mockResolvedValue({ success: true });

    render(
      <SymbolProvider>
        <ExecutionPage />
      </SymbolProvider>
    );

    await waitFor(() => {
      const clearButton = screen.getByLabelText('Clear Override');
      fireEvent.click(clearButton);
    });

    await waitFor(() => {
      expect(orchestrationApi.clearExecutionOverride).toHaveBeenCalledWith('BANKNIFTY', '5m');
    });
  });
});

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import RunsPage from '../pages/RunsPage';
import { SymbolProvider } from '../context/SymbolContext';
import * as orchestrationApi from '../api/orchestrationApi';

vi.mock('../api/orchestrationApi');

const mockRuns: orchestrationApi.OrchestrationRun[] = [
  {
    id: 1,
    run_type: 'train',
    mode: 'explicit',
    interval: '5m',
    status: 'completed',
    selected_symbols_count: 5,
    ready_symbols_count: 5,
    success_count: 5,
    skipped_count: 0,
    failed_count: 0,
    summary: { model_id: 'm1' },
    created_ts: new Date().toISOString()
  },
  {
    id: 2,
    run_type: 'execution',
    mode: 'explicit',
    interval: '5m',
    status: 'failed',
    reason: 'Connection error',
    selected_symbols_count: 5,
    ready_symbols_count: 3,
    success_count: 2,
    skipped_count: 0,
    failed_count: 1,
    summary: { orders: [] },
    created_ts: new Date().toISOString()
  }
];

describe('RunsPage', () => {
  beforeEach(() => {
    vi.mocked(orchestrationApi.getOrchestrationRuns).mockResolvedValue(mockRuns);
    vi.mocked(orchestrationApi.getOrchestrationRun).mockImplementation(async (id) => {
      const run = mockRuns.find(r => r.id === id);
      if (!run) throw new Error('Not found');
      return run;
    });
  });

  it('renders runs list correctly', async () => {
    render(
      <SymbolProvider>
        <RunsPage />
      </SymbolProvider>
    );

    expect(await screen.findByText(/train/i)).toBeInTheDocument();
    expect(screen.getAllByText(/explicit/i).length).toBeGreaterThan(0);
  });

  it('filters runs by type', async () => {
    render(
      <SymbolProvider>
        <RunsPage />
      </SymbolProvider>
    );

    const filterSelect = screen.getByLabelText(/filter by type/i);
    fireEvent.change(filterSelect, { target: { value: 'train' } });

    await waitFor(() => {
      expect(orchestrationApi.getOrchestrationRuns).toHaveBeenCalledWith('train', expect.any(Number));
    });
  });

  it('shows run details when a row is clicked', async () => {
    render(
      <SymbolProvider>
        <RunsPage />
      </SymbolProvider>
    );

    await waitFor(() => {
      const row = screen.getByTestId('run-row-1');
      fireEvent.click(row);
    });

    expect(await screen.findByText(/run #1/i)).toBeInTheDocument();
    expect(await screen.findByText(/model id/i)).toBeInTheDocument();
    expect(await screen.findByText('m1')).toBeInTheDocument();
  });

  it('renders failure reason when present', async () => {
    render(
      <SymbolProvider>
        <RunsPage />
      </SymbolProvider>
    );

    await waitFor(() => {
      const row = screen.getByTestId('run-row-2');
      fireEvent.click(row);
    });

    await waitFor(() => {
      expect(screen.getByText('FAILURE REASON')).toBeInTheDocument();
      expect(screen.getByText('Connection error')).toBeInTheDocument();
    });
  });

  it('handles empty runs state', async () => {
    vi.mocked(orchestrationApi.getOrchestrationRuns).mockResolvedValue([]);

    render(
      <SymbolProvider>
        <RunsPage />
      </SymbolProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('No orchestration runs found.')).toBeInTheDocument();
    });
  });

  it('renders error when detail fetch fails', async () => {
    vi.mocked(orchestrationApi.getOrchestrationRun).mockRejectedValue(new Error('Detail fetch failed'));

    render(
      <SymbolProvider>
        <RunsPage />
      </SymbolProvider>
    );

    await waitFor(() => {
      const row = screen.getByTestId('run-row-1');
      fireEvent.click(row);
    });

    expect(await screen.findByText('Detail fetch failed')).toBeInTheDocument();
    // Verify list is still present
    expect(screen.getByTestId('run-row-2')).toBeInTheDocument();
  });
});

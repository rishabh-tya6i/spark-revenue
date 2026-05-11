import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import OperationsPage from '../pages/OperationsPage';
import { SymbolProvider } from '../context/SymbolContext';
import * as orchestrationApi from '../api/orchestrationApi';

vi.mock('../api/orchestrationApi');

describe('OperationsPage', () => {
  it('triggers training flow on button click', async () => {
    vi.mocked(orchestrationApi.runTrainTrainable).mockResolvedValue({
      status: 'COMPLETED',
      run_record_id: 500,
      summary: { prepared: 5, trained: 3 }
    });

    render(
      <SymbolProvider>
        <OperationsPage />
      </SymbolProvider>
    );

    fireEvent.click(screen.getByText('Run Model Training'));

    expect(orchestrationApi.runTrainTrainable).toHaveBeenCalled();
    expect(await screen.findByText('COMPLETED')).toBeInTheDocument();
    expect(await screen.findByText('RUN ID: 500')).toBeInTheDocument();
    expect(await screen.findByText(/PREPARED/i)).toBeInTheDocument();
  });

  it('triggers inference flow on button click', async () => {
    vi.mocked(orchestrationApi.runUniverseInference).mockResolvedValue({
      status: 'SUCCESS',
      run_record_id: 501,
      summary: { symbols: 10, inferences: 10 }
    });

    render(
      <SymbolProvider>
        <OperationsPage />
      </SymbolProvider>
    );

    fireEvent.click(screen.getByText('Run Universe Inference'));

    expect(orchestrationApi.runUniverseInference).toHaveBeenCalled();
    expect(await screen.findByText('RUN ID: 501')).toBeInTheDocument();
  });
});

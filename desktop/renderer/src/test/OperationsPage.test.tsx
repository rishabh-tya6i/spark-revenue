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

    fireEvent.click(screen.getByText('Execute Training Flow'));

    await waitFor(() => {
      expect(orchestrationApi.runTrainTrainable).toHaveBeenCalled();
      expect(screen.getByText('COMPLETED')).toBeInTheDocument();
      expect(screen.getByText('RUN: 500')).toBeInTheDocument();
      expect(screen.getByText('PREPARED')).toBeInTheDocument();
    });
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

    fireEvent.click(screen.getByText('Run All Inferences'));

    await waitFor(() => {
      expect(orchestrationApi.runUniverseInference).toHaveBeenCalled();
      expect(screen.getByText('RUN: 501')).toBeInTheDocument();
    });
  });
});

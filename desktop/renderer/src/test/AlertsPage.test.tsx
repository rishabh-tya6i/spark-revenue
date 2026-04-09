import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AlertsPage from '../pages/AlertsPage';
import * as alertsApi from '../api/alertsApi';

vi.mock('../api/alertsApi');

const mockAlerts = [
  {
    id: 1,
    symbol: 'BTCUSDT',
    interval: '5m',
    timestamp: new Date().toISOString(),
    alert_type: 'HIGH_CONFIDENCE_BUY',
    message: 'Test alert message',
    importance: 0.9,
    delivered_channels: 'desktop',
  },
];

describe('AlertsPage', () => {
  it('renders alerts list', async () => {
    vi.mocked(alertsApi.getRecentAlerts).mockResolvedValue(mockAlerts);

    render(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText('Test alert message')).toBeInTheDocument();
      expect(screen.getByText('HIGH_CONFIDENCE_BUY')).toBeInTheDocument();
      expect(screen.getByText('90')).toBeInTheDocument();
    });
  });
});

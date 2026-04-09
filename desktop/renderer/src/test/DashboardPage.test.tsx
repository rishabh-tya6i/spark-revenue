import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import DashboardPage from '../pages/DashboardPage';
import { SymbolProvider } from '../context/SymbolContext';
import * as decisionApi from '../api/decisionApi';
import * as optionsApi from '../api/optionsApi';
import * as sentimentApi from '../api/sentimentApi';

vi.mock('../api/decisionApi');
vi.mock('../api/optionsApi');
vi.mock('../api/sentimentApi');

const mockDecision = {
  symbol: 'BTCUSDT',
  interval: '5m',
  timestamp: new Date().toISOString(),
  decision_label: 'STRONG_BULLISH',
  decision_score: 0.85,
  price_direction: 'BULLISH',
  price_confidence: 0.9,
  rl_action: 'BUY',
  rl_confidence: 0.8,
  sentiment_score: 0.6,
  sentiment_label: 'POSITIVE',
  options_signal_label: 'CALL_BUILDUP',
  options_pcr: 0.7,
  options_max_pain_strike: 45000,
};

const mockOptions = {
  symbol: 'BTCUSDT',
  expiry: '2023-12-31',
  timestamp: new Date().toISOString(),
  pcr: 0.7,
  max_pain_strike: 45000,
  call_oi_total: 1000,
  put_oi_total: 700,
  signal_label: 'CALL_BUILDUP',
  signal_strength: 0.8,
};

const mockSentiment = [
  { news_id: 1, sentiment_score: 0.8, sentiment_label: 'POSITIVE', model_name: 'test', created_ts: new Date().toISOString() }
];

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.mocked(decisionApi.getLatestDecision).mockResolvedValue(mockDecision);
    vi.mocked(optionsApi.getOptionsSignal).mockResolvedValue(mockOptions);
    vi.mocked(sentimentApi.getLatestSentiment).mockResolvedValue(mockSentiment);
  });

  it('renders decision label and score', async () => {
    render(
      <SymbolProvider>
        <DashboardPage />
      </SymbolProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('STRONG_BULLISH')).toBeInTheDocument();
      expect(screen.getByText('85.0%')).toBeInTheDocument();
    });
  });

  it('renders options signal card', async () => {
    render(
      <SymbolProvider>
        <DashboardPage />
      </SymbolProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Options Intel')).toBeInTheDocument();
      expect(screen.getByText('0.700')).toBeInTheDocument();
      expect(screen.getByText('$45,000')).toBeInTheDocument();
    });
  });

  it('renders sentiment headlines', async () => {
    render(
      <SymbolProvider>
        <DashboardPage />
      </SymbolProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('News Item #1')).toBeInTheDocument();
    });
  });
});

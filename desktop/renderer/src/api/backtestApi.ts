import client from './client';

export interface BacktestRequestDTO {
  strategy_name: string;
  symbol: string;
  interval: string;
  start_ts: string;
  end_ts: string;
  initial_capital?: number;
}

export interface BacktestRunOut {
  id: number;
  strategy_name: string;
  symbol: string;
  interval: string;
  start_ts: string;
  end_ts: string;
  initial_capital: number;
  final_capital?: number;
  status: string;
  created_ts: string;
  completed_ts?: string;
  details?: string;
}

export interface BacktestMetricsOut {
  backtest_id: number;
  metrics: {
    win_rate: number;
    max_drawdown: number;
    sharpe: number;
    [key: string]: number;
  };
}

export const runBacktest = async (request: BacktestRequestDTO): Promise<{ run: BacktestRunOut; metrics: BacktestMetricsOut }> => {
  const response = await client.post<{ run: BacktestRunOut; metrics: BacktestMetricsOut }>('/backtest/run', request);
  return response.data;
};

export const getBacktestRun = async (runId: number): Promise<BacktestRunOut> => {
  const response = await client.get<BacktestRunOut>(`/backtest/run/${runId}`);
  return response.data;
};

export const getBacktestMetrics = async (runId: number): Promise<BacktestMetricsOut> => {
  const response = await client.get<BacktestMetricsOut>(`/backtest/metrics/${runId}`);
  return response.data;
};

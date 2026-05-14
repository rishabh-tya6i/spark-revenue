import client from './client';

export type IngestionSource = 'upstox' | 'binance';

export interface BackfillParams {
  source: IngestionSource;
  symbol: string;
  start: string; // YYYY-MM-DD
  end: string; // YYYY-MM-DD
  interval?: string;
}

export const backfillOhlc = async (params: BackfillParams): Promise<any> => {
  const response = await client.post('/ingestion/backfill', null, { params });
  return response.data;
};


import client from './client';

export interface InstrumentResolveResult {
  symbol: string;
  instrument_key: string;
  segment: string;
  exchange: string;
  instrument_type: string;
  trading_symbol?: string;
  name?: string;
}

export const syncInstruments = async (segments?: string): Promise<{ processed_count: number }> => {
  const response = await client.post('/instruments/sync', null, { params: { segments } });
  return response.data;
};

export const resolveInstrument = async (symbol: string): Promise<InstrumentResolveResult> => {
  const response = await client.get('/instruments/resolve', { params: { symbol } });
  return response.data;
};


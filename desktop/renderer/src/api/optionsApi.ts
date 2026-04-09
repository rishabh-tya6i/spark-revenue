import client from './client';

export interface OptionSignalOut {
  symbol: string;
  expiry: string;
  timestamp: string;
  pcr: number;
  max_pain_strike: number;
  call_oi_total: number;
  put_oi_total: number;
  signal_label: string;
  signal_strength: number;
}

export const getOptionsSignal = async (symbol: string, expiry?: string): Promise<OptionSignalOut | null> => {
  try {
    const response = await client.get<OptionSignalOut>('/options/signal', {
      params: { symbol, expiry },
    });
    return response.data;
  } catch (error: any) {
    if (error.response?.status === 404) return null;
    throw error;
  }
};

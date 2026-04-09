import client from './client';

export interface FusedDecisionDTO {
  symbol: string;
  interval: string;
  timestamp: string;
  decision_label: string;
  decision_score: number;
  price_direction: string;
  price_confidence: number;
  rl_action: string;
  rl_confidence: number;
  sentiment_score: number;
  sentiment_label: string;
  options_signal_label: string;
  options_pcr: number;
  options_max_pain_strike: number;
}

export const getLatestDecision = async (symbol: string, interval: string): Promise<FusedDecisionDTO> => {
  const response = await client.get<FusedDecisionDTO>('/decision/latest', {
    params: { symbol, interval },
  });
  return response.data;
};

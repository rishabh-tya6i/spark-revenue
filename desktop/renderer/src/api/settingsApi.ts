import client from './client';

export interface TokenStatus {
  present: boolean;
  masked: string;
  source: string;
}

export const getUpstoxTokenStatus = async (): Promise<TokenStatus> => {
  const response = await client.get('/settings/upstox-token');
  return response.data;
};

export const setUpstoxToken = async (token: string): Promise<any> => {
  const response = await client.post('/settings/upstox-token', { token });
  return response.data;
};

export const clearUpstoxToken = async (): Promise<any> => {
  const response = await client.delete('/settings/upstox-token');
  return response.data;
};


import client from './client';

export interface AlertDTO {
  id: number;
  symbol: string;
  interval: string;
  timestamp: string;
  alert_type: string;
  message: string;
  importance: number;
  delivered_channels: string;
}

export const getRecentAlerts = async (limit: number = 20): Promise<AlertDTO[]> => {
  const response = await client.get<AlertDTO[]>('/alerts/recent', {
    params: { limit },
  });
  return response.data;
};

import client from './client';

export interface NewsSentimentOut {
  news_id: number;
  sentiment_score: number;
  sentiment_label: string;
  model_name: string;
  created_ts: string;
}

export const getLatestSentiment = async (limit: number = 20): Promise<NewsSentimentOut[]> => {
  const response = await client.get<NewsSentimentOut[]>('/sentiment/latest', {
    params: { limit },
  });
  return response.data;
};

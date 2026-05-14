import axios from 'axios';
import { BACKEND_BASE_URL } from './config';

const client = axios.create({
  baseURL: BACKEND_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    // Treat "not found" as a normal state for optional widgets (e.g. options signals).
    if (status === 404) {
      console.debug('API 404:', error.response?.data || error.message);
    } else {
      console.error('API Error:', error.response?.data || error.message);
    }
    return Promise.reject(error);
  }
);

export default client;

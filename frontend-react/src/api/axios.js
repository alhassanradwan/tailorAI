import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Storage keys (must match AuthContext)
const STORAGE_PREFIX = 'adaptiveai';
const gk = (name) => `${STORAGE_PREFIX}:global:${name}`;

function getToken() {
  return localStorage.getItem(gk('access_token')) || localStorage.getItem('access_token');
}

function getRefreshToken() {
  return localStorage.getItem(gk('refresh_token')) || localStorage.getItem('refresh_token');
}

function clearAllTokens() {
  localStorage.removeItem(gk('access_token'));
  localStorage.removeItem(gk('refresh_token'));
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

// Request interceptor — attach access token
api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Refresh lock: prevents multiple concurrent refresh attempts ──
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

// Response interceptor — auto-refresh on 401 (NO window.location redirects)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      // If already refreshing, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        }).catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;

      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        // No refresh token — just clear tokens and reject (React handles redirect)
        clearAllTokens();
        return Promise.reject(error);
      }

      isRefreshing = true;

      try {
        const res = await axios.post(`${API_BASE_URL}/auth/refresh`, null, {
          headers: { Authorization: `Bearer ${refreshToken}` },
        });

        const newAccessToken = res.data.access_token;
        localStorage.setItem(gk('access_token'), newAccessToken);
        localStorage.setItem('access_token', newAccessToken);

        isRefreshing = false;
        processQueue(null, newAccessToken);

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        isRefreshing = false;
        processQueue(refreshError, null);
        // Refresh failed — clear tokens, let React handle logout
        clearAllTokens();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
export { API_BASE_URL };

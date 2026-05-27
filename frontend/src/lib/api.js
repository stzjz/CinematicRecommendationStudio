const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

const jsonHeaders = {
  Accept: 'application/json',
};

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`, { headers: jsonHeaders });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${path}`);
  }
  return response.json();
}

export function fetchHealth() {
  return request('/health');
}

export function fetchUsers() {
  return request('/users');
}

export function fetchAlgorithms() {
  return request('/algorithms');
}

export function fetchHotMovies(limit = 6) {
  return request(`/movies/hot?limit=${limit}`);
}

export function fetchRecommendations(userId, algorithm, limit = 6) {
  return request(`/recommendations/${userId}?algorithm=${algorithm}&limit=${limit}`);
}

export function fetchHistory(userId) {
  return request(`/users/${userId}/history`);
}

export function fetchMetrics() {
  return request('/metrics/models');
}

export function fetchAblation() {
  return request('/metrics/ablation');
}

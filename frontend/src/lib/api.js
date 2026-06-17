const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

const jsonHeaders = {
  Accept: 'application/json',
};

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, { headers: jsonHeaders, ...options });
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

export function createUser(payload) {
  return request('/users', {
    method: 'POST',
    headers: {
      ...jsonHeaders,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export function fetchAlgorithms() {
  return request('/algorithms');
}

export function fetchHotMovies(limit = 6) {
  return request(`/movies/hot?limit=${limit}`);
}

export function fetchHotMovieBoards(limitPerGenre = 5, maxBoards = 6) {
  return request(`/movies/hot/boards?limit_per_genre=${limitPerGenre}&max_boards=${maxBoards}`);
}

export function fetchMovieDetail(movieId) {
  return request(`/movies/${movieId}`);
}

export function fetchMovieRatings(movieId, limit = 8, offset = 0) {
  return request(`/movies/${movieId}/ratings?limit=${limit}&offset=${offset}`);
}

export function searchMovies(query, limit = 20) {
  return request(`/movies/search?q=${encodeURIComponent(query)}&limit=${limit}`);
}

export function fetchRecommendations(userId, algorithm, limit = 6, options = {}) {
  const params = new URLSearchParams({
    algorithm,
    limit: String(limit),
  });
  if (options.genreWeight !== undefined) {
    params.set('genre_weight', String(options.genreWeight));
  }
  if (options.tagWeight !== undefined) {
    params.set('tag_weight', String(options.tagWeight));
  }
  return request(`/recommendations/${userId}?${params.toString()}`);
}

export function fetchHistory(userId) {
  return request(`/users/${userId}/history`);
}

export function fetchPreferenceProfile(userId, window = 'all') {
  return request(`/users/${userId}/preference-profile?window=${window}`);
}

export function fetchUserMovieRating(userId, movieId) {
  return request(`/users/${userId}/ratings/${movieId}`);
}

export function saveUserRating(userId, payload) {
  return request(`/users/${userId}/ratings`, {
    method: 'POST',
    headers: {
      ...jsonHeaders,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export function updateUserRating(userId, movieId, payload) {
  return request(`/users/${userId}/ratings/${movieId}`, {
    method: 'PUT',
    headers: {
      ...jsonHeaders,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export function deleteUserRating(userId, movieId) {
  return request(`/users/${userId}/ratings/${movieId}`, { method: 'DELETE' });
}

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    occupation TEXT
);

CREATE TABLE movies (
    movie_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    year INTEGER,
    poster_url TEXT,
    summary TEXT,
    genres TEXT NOT NULL
);

CREATE TABLE ratings (
    rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    rating REAL NOT NULL,
    rated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);

CREATE TABLE recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    algorithm_name TEXT NOT NULL,
    score REAL NOT NULL,
    rank_position INTEGER NOT NULL,
    reason TEXT,
    generated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);

CREATE TABLE model_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    hr10 REAL NOT NULL,
    ndcg10 REAL NOT NULL,
    remark TEXT
);

CREATE TABLE ablation_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    embedding_dim INTEGER,
    negative_ratio INTEGER,
    mlp_layers INTEGER,
    hr10 REAL NOT NULL,
    ndcg10 REAL NOT NULL
);

CREATE TABLE training_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    epoch INTEGER NOT NULL,
    loss REAL,
    hr10 REAL,
    ndcg10 REAL
);

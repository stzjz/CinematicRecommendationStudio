CREATE TABLE users (
    user_id INT PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    age INT,
    gender VARCHAR(16),
    occupation VARCHAR(64)
);

CREATE TABLE movies (
    movie_id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    year INT,
    poster_url VARCHAR(512),
    summary TEXT,
    genres VARCHAR(255) NOT NULL
);

CREATE TABLE ratings (
    rating_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    rating DECIMAL(2,1) NOT NULL,
    rated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);

CREATE TABLE recommendations (
    recommendation_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    algorithm_name VARCHAR(64) NOT NULL,
    score DECIMAL(8,4) NOT NULL,
    rank_position INT NOT NULL,
    reason VARCHAR(255),
    generated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);

CREATE TABLE model_metrics (
    metric_id INT PRIMARY KEY AUTO_INCREMENT,
    model_name VARCHAR(64) NOT NULL,
    hr10 DECIMAL(6,4) NOT NULL,
    ndcg10 DECIMAL(6,4) NOT NULL,
    remark VARCHAR(255)
);

CREATE TABLE ablation_results (
    result_id INT PRIMARY KEY AUTO_INCREMENT,
    model_name VARCHAR(64) NOT NULL,
    embedding_dim INT,
    negative_ratio INT,
    mlp_layers INT,
    hr10 DECIMAL(6,4) NOT NULL,
    ndcg10 DECIMAL(6,4) NOT NULL
);

CREATE TABLE training_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    model_name VARCHAR(64) NOT NULL,
    epoch INT NOT NULL,
    loss DECIMAL(10,6),
    hr10 DECIMAL(6,4),
    ndcg10 DECIMAL(6,4)
);

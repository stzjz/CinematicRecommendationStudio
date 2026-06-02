import os
import sqlite3

from app.poster_catalog import poster_url_for_movie
from app.sample_data import ABLATION_RESULTS, MODEL_METRICS, MOVIES, RATINGS, USERS


def _normalize_genres(raw_value):
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split("|") if item.strip()]


class InMemoryRepository(object):
    def load(self):
        return {
            "users": USERS,
            "movies": MOVIES,
            "ratings": RATINGS,
            "movie_tags": [],
            "model_metrics": MODEL_METRICS,
            "ablation_results": ABLATION_RESULTS,
            "data_source": "memory",
        }


class SQLiteRepository(object):
    def __init__(self, db_path):
        self.db_path = db_path

    def exists(self):
        return os.path.exists(self.db_path)

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def load(self):
        connection = self._connect()
        try:
            self._ensure_runtime_indexes(connection)
            users = self._fetch_users(connection)
            movies = self._fetch_movies(connection)
            ratings = self._fetch_ratings(connection)
            movie_tags = self._fetch_movie_tags(connection)
            model_metrics = self._fetch_model_metrics(connection)
            ablation_results = self._fetch_ablation_results(connection)
        finally:
            connection.close()

        return {
            "users": users,
            "movies": movies,
            "ratings": ratings,
            "movie_tags": movie_tags,
            "model_metrics": model_metrics,
            "ablation_results": ablation_results,
            "data_source": "sqlite",
            "db_path": self.db_path,
        }

    def _ensure_runtime_indexes(self, connection):
        statements = [
            "CREATE INDEX IF NOT EXISTS idx_ratings_movie_id ON ratings(movie_id)",
            "CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON ratings(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_ratings_user_movie ON ratings(user_id, movie_id)",
            "CREATE INDEX IF NOT EXISTS idx_movie_tags_movie_id ON movie_tags(movie_id)",
            "CREATE INDEX IF NOT EXISTS idx_movie_tags_user_id ON movie_tags(user_id)",
            """
            CREATE TABLE IF NOT EXISTS movie_rating_stats (
                movie_id INTEGER PRIMARY KEY,
                rating_count INTEGER NOT NULL,
                average_rating REAL NOT NULL
            )
            """,
        ]
        for statement in statements:
            connection.execute(statement)
        rating_columns = [row["name"] for row in connection.execute("PRAGMA table_info(ratings)").fetchall()]
        if "comment" not in rating_columns:
            connection.execute("ALTER TABLE ratings ADD COLUMN comment TEXT")
        stat_count = connection.execute("SELECT COUNT(*) AS count FROM movie_rating_stats").fetchone()["count"]
        if stat_count == 0:
            connection.execute(
                """
                INSERT INTO movie_rating_stats (movie_id, rating_count, average_rating)
                SELECT movie_id, COUNT(*) AS rating_count, AVG(rating) AS average_rating
                FROM ratings
                GROUP BY movie_id
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_movie_rating_stats_count ON movie_rating_stats(rating_count DESC)")
        connection.commit()

    def _fetch_users(self, connection):
        query = """
        SELECT user_id, username, age, gender, occupation
        FROM users
        ORDER BY user_id
        """
        rows = connection.execute(query).fetchall()
        return [dict(row) for row in rows]

    def _fetch_movies(self, connection):
        query = """
        SELECT movie_id, title, year, poster_url, summary, genres
        FROM movies
        ORDER BY movie_id
        """
        rows = connection.execute(query).fetchall()
        movies = []
        for row in rows:
            movie = dict(row)
            movie["genres"] = _normalize_genres(movie.get("genres"))
            movie["poster_url"] = poster_url_for_movie(movie.get("title"), movie.get("year"), movie.get("poster_url"))
            movies.append(movie)
        return movies

    def _fetch_ratings(self, connection):
        query = """
        SELECT user_id, movie_id, rating, rated_at, comment
        FROM ratings
        ORDER BY rating_id
        LIMIT 200000
        """
        rows = connection.execute(query).fetchall()
        return [dict(row) for row in rows]

    def _has_table(self, connection, table_name):
        query = "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?"
        return connection.execute(query, (table_name,)).fetchone() is not None

    def _fetch_movie_tags(self, connection):
        if not self._has_table(connection, "movie_tags"):
            return []
        query = """
        SELECT user_id, movie_id, tag, tagged_at
        FROM movie_tags
        ORDER BY tag_id
        """
        rows = connection.execute(query).fetchall()
        return [dict(row) for row in rows]

    def _fetch_model_metrics(self, connection):
        query = """
        SELECT model_name, hr10, ndcg10, remark
        FROM model_metrics
        ORDER BY model_name
        """
        rows = connection.execute(query).fetchall()
        return [dict(row) for row in rows]

    def _fetch_ablation_results(self, connection):
        query = """
        SELECT model_name, embedding_dim, negative_ratio, mlp_layers, hr10, ndcg10
        FROM ablation_results
        ORDER BY model_name, embedding_dim, negative_ratio, mlp_layers
        """
        rows = connection.execute(query).fetchall()
        return [dict(row) for row in rows]


def load_dataset(data_source, db_path):
    source = data_source or "auto"
    sqlite_repository = SQLiteRepository(db_path)

    if source == "sqlite":
        if not sqlite_repository.exists():
            raise RuntimeError("SQLite database not found: %s" % db_path)
        return sqlite_repository.load()

    if source == "memory":
        return InMemoryRepository().load()

    if sqlite_repository.exists():
        return sqlite_repository.load()

    return InMemoryRepository().load()

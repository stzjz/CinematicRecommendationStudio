import os
import sqlite3

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
            users = self._fetch_users(connection)
            movies = self._fetch_movies(connection)
            ratings = self._fetch_ratings(connection)
            model_metrics = self._fetch_model_metrics(connection)
            ablation_results = self._fetch_ablation_results(connection)
        finally:
            connection.close()

        return {
            "users": users,
            "movies": movies,
            "ratings": ratings,
            "model_metrics": model_metrics,
            "ablation_results": ablation_results,
            "data_source": "sqlite",
        }

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
            movies.append(movie)
        return movies

    def _fetch_ratings(self, connection):
        query = """
        SELECT user_id, movie_id, rating
        FROM ratings
        ORDER BY rating_id
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

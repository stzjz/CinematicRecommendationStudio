import os
import sys
import sqlite3

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import DEFAULT_DB_PATH
from app.sample_data import ABLATION_RESULTS, MODEL_METRICS, MOVIES, RATINGS, USERS


SCHEMA_PATH = os.path.join(BACKEND_DIR, "sql", "schema_sqlite.sql")


def ensure_parent(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent)


def load_schema():
    with open(SCHEMA_PATH, "r") as handle:
        return handle.read()


def seed_users(connection):
    query = """
    INSERT INTO users (user_id, username, age, gender, occupation)
    VALUES (?, ?, ?, ?, ?)
    """
    rows = [(item["user_id"], item["username"], item["age"], item["gender"], item["occupation"]) for item in USERS]
    connection.executemany(query, rows)


def seed_movies(connection):
    query = """
    INSERT INTO movies (movie_id, title, year, poster_url, summary, genres)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    rows = []
    for item in MOVIES:
        rows.append(
            (
                item["movie_id"],
                item["title"],
                item["year"],
                item["poster_url"],
                item["summary"],
                "|".join(item["genres"]),
            )
        )
    connection.executemany(query, rows)


def seed_ratings(connection):
    query = """
    INSERT INTO ratings (user_id, movie_id, rating, rated_at)
    VALUES (?, ?, ?, ?)
    """
    rows = []
    for index, item in enumerate(RATINGS):
        rows.append(
            (
                item["user_id"],
                item["movie_id"],
                item["rating"],
                "2026-05-%02d" % (12 + (index % 18)),
            )
        )
    connection.executemany(query, rows)


def seed_model_metrics(connection):
    query = """
    INSERT INTO model_metrics (model_name, hr10, ndcg10, remark)
    VALUES (?, ?, ?, ?)
    """
    rows = [(item["model_name"], item["hr10"], item["ndcg10"], item["remark"]) for item in MODEL_METRICS]
    connection.executemany(query, rows)


def seed_ablation_results(connection):
    query = """
    INSERT INTO ablation_results (model_name, embedding_dim, negative_ratio, mlp_layers, hr10, ndcg10)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    rows = []
    for item in ABLATION_RESULTS:
        rows.append(
            (
                item["model_name"],
                item["embedding_dim"],
                item["negative_ratio"],
                item["mlp_layers"],
                item["hr10"],
                item["ndcg10"],
            )
        )
    connection.executemany(query, rows)


def initialize_database(db_path=DEFAULT_DB_PATH):
    ensure_parent(db_path)
    if os.path.exists(db_path):
        os.remove(db_path)

    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(load_schema())
        seed_users(connection)
        seed_movies(connection)
        seed_ratings(connection)
        seed_model_metrics(connection)
        seed_ablation_results(connection)
        connection.commit()
    finally:
        connection.close()

    return db_path


if __name__ == "__main__":
    path = initialize_database()
    print("Initialized SQLite database at %s" % path)

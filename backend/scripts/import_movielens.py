import os
import re
import sqlite3
import sys
import zipfile

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import DEFAULT_DB_PATH
from scripts.init_sqlite import ensure_parent, load_schema, seed_ablation_results, seed_model_metrics


DEFAULT_ARCHIVE_PATH = os.path.join(BACKEND_DIR, "data", "raw", "ml-1m.zip")
MOVIE_YEAR_PATTERN = re.compile(r"^(.*) \((\d{4})\)$")


def _decode_lines(archive, member_name):
    with archive.open(member_name) as handle:
        for raw_line in handle:
            yield raw_line.decode("latin-1").rstrip("\r\n")


def _parse_title(raw_title):
    match = MOVIE_YEAR_PATTERN.match(raw_title)
    if not match:
        return raw_title, None
    return match.group(1), int(match.group(2))


def _seed_users(connection, archive):
    rows = []
    for line in _decode_lines(archive, "ml-1m/users.dat"):
        user_id, gender, age, occupation, _zip_code = line.split("::")
        rows.append((int(user_id), "movielens-%s" % user_id, int(age), gender, occupation))

    connection.executemany(
        """
        INSERT INTO users (user_id, username, age, gender, occupation)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def _seed_movies(connection, archive):
    rows = []
    for line in _decode_lines(archive, "ml-1m/movies.dat"):
        movie_id, raw_title, genres = line.split("::")
        title, year = _parse_title(raw_title)
        rows.append((int(movie_id), title, year, "/api/posters/%s.svg" % movie_id, "", genres))

    connection.executemany(
        """
        INSERT INTO movies (movie_id, title, year, poster_url, summary, genres)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def _seed_ratings(connection, archive):
    rows = []
    total = 0
    for line in _decode_lines(archive, "ml-1m/ratings.dat"):
        user_id, movie_id, rating, rated_at = line.split("::")
        rows.append((int(user_id), int(movie_id), float(rating), rated_at))
        total += 1
        if len(rows) >= 10000:
            connection.executemany(
                """
                INSERT INTO ratings (user_id, movie_id, rating, rated_at)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )
            rows = []

    if rows:
        connection.executemany(
            """
            INSERT INTO ratings (user_id, movie_id, rating, rated_at)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
    return total


def import_movielens(archive_path=DEFAULT_ARCHIVE_PATH, db_path=DEFAULT_DB_PATH):
    if not os.path.exists(archive_path):
        raise RuntimeError("MovieLens archive not found: %s" % archive_path)

    ensure_parent(db_path)
    if os.path.exists(db_path):
        os.remove(db_path)

    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(load_schema())
        with zipfile.ZipFile(archive_path) as archive:
            user_count = _seed_users(connection, archive)
            movie_count = _seed_movies(connection, archive)
            rating_count = _seed_ratings(connection, archive)
        seed_model_metrics(connection)
        seed_ablation_results(connection)
        connection.commit()
    finally:
        connection.close()

    return {
        "db_path": db_path,
        "users": user_count,
        "movies": movie_count,
        "ratings": rating_count,
    }


if __name__ == "__main__":
    result = import_movielens()
    print(
        "Imported MovieLens-1M into %(db_path)s: "
        "%(users)s users, %(movies)s movies, %(ratings)s ratings" % result
    )

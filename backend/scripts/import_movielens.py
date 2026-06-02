import os
import re
import sqlite3
import sys
import zipfile
import csv
from io import TextIOWrapper

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import DEFAULT_DB_PATH
from app.poster_catalog import poster_url_for_movie
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


def _collect_dat_user_ids(archive):
    user_ids = set()
    for suffix in ("ratings.dat", "tags.dat"):
        member_name = _find_archive_member(archive, suffix)
        if not member_name:
            continue
        for line in _decode_lines(archive, member_name):
            parts = line.split("::")
            if parts and parts[0]:
                user_ids.add(int(parts[0]))
    return user_ids


def _seed_users(connection, archive):
    member_name = _find_archive_member(archive, "users.dat")
    if not member_name:
        rows = [(user_id, "movielens-%s" % user_id, None, None, None) for user_id in sorted(_collect_dat_user_ids(archive))]
        connection.executemany(
            """
            INSERT INTO users (user_id, username, age, gender, occupation)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)

    rows = []
    for line in _decode_lines(archive, member_name):
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


def _seed_csv_users(connection, archive):
    user_ids = set()
    for suffix in ("ratings.csv", "tags.csv"):
        member_name = _find_archive_member(archive, suffix)
        if not member_name:
            continue
        with archive.open(member_name) as handle:
            reader = csv.DictReader(TextIOWrapper(handle, encoding="utf-8"))
            for item in reader:
                if item.get("userId"):
                    user_ids.add(int(item["userId"]))

    rows = [(user_id, "movielens-%s" % user_id, None, None, None) for user_id in sorted(user_ids)]
    connection.executemany(
        """
        INSERT INTO users (user_id, username, age, gender, occupation)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def _seed_movies(connection, archive):
    member_name = _find_archive_member(archive, "movies.dat")
    rows = []
    for line in _decode_lines(archive, member_name):
        movie_id, raw_title, genres = line.split("::")
        title, year = _parse_title(raw_title)
        fallback_poster = "/api/posters/%s.svg" % movie_id
        rows.append((int(movie_id), title, year, poster_url_for_movie(title, year, fallback_poster), "", genres))

    connection.executemany(
        """
        INSERT INTO movies (movie_id, title, year, poster_url, summary, genres)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def _seed_csv_movies(connection, archive):
    member_name = _find_archive_member(archive, "movies.csv")
    rows = []
    with archive.open(member_name) as handle:
        reader = csv.DictReader(TextIOWrapper(handle, encoding="utf-8"))
        for item in reader:
            title, year = _parse_title(item["title"])
            fallback_poster = "/api/posters/%s.svg" % item["movieId"]
            rows.append(
                (
                    int(item["movieId"]),
                    title,
                    year,
                    poster_url_for_movie(title, year, fallback_poster),
                    "",
                    item["genres"],
                )
            )

    connection.executemany(
        """
        INSERT INTO movies (movie_id, title, year, poster_url, summary, genres)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def _seed_ratings(connection, archive):
    member_name = _find_archive_member(archive, "ratings.dat")
    rows = []
    total = 0
    for line in _decode_lines(archive, member_name):
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


def _seed_csv_ratings(connection, archive):
    member_name = _find_archive_member(archive, "ratings.csv")
    rows = []
    total = 0
    with archive.open(member_name) as handle:
        reader = csv.DictReader(TextIOWrapper(handle, encoding="utf-8"))
        for item in reader:
            rows.append((int(item["userId"]), int(item["movieId"]), float(item["rating"]), item.get("timestamp")))
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


def _find_archive_member(archive, suffix):
    for name in archive.namelist():
        if name.lower().endswith(suffix.lower()):
            return name
    return None


def _seed_tags(connection, archive):
    member_name = _find_archive_member(archive, "tags.csv")
    if not member_name:
        return _seed_dat_tags(connection, archive)

    rows = []
    total = 0
    with archive.open(member_name) as handle:
        reader = csv.DictReader(TextIOWrapper(handle, encoding="utf-8"))
        for item in reader:
            rows.append((int(item["userId"]), int(item["movieId"]), item["tag"], item.get("timestamp")))
            total += 1
            if len(rows) >= 10000:
                connection.executemany(
                    """
                    INSERT INTO movie_tags (user_id, movie_id, tag, tagged_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    rows,
                )
                rows = []

    if rows:
        connection.executemany(
            """
            INSERT INTO movie_tags (user_id, movie_id, tag, tagged_at)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
    return total


def _seed_dat_tags(connection, archive):
    member_name = _find_archive_member(archive, "tags.dat")
    if not member_name:
        return 0

    rows = []
    total = 0
    for line in _decode_lines(archive, member_name):
        user_id, movie_id, tag, tagged_at = line.split("::")
        rows.append((int(user_id), int(movie_id), tag, tagged_at))
        total += 1
        if len(rows) >= 10000:
            connection.executemany(
                """
                INSERT INTO movie_tags (user_id, movie_id, tag, tagged_at)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )
            rows = []

    if rows:
        connection.executemany(
            """
            INSERT INTO movie_tags (user_id, movie_id, tag, tagged_at)
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
            if _find_archive_member(archive, "movies.csv") and _find_archive_member(archive, "ratings.csv"):
                user_count = _seed_csv_users(connection, archive)
                movie_count = _seed_csv_movies(connection, archive)
                rating_count = _seed_csv_ratings(connection, archive)
            else:
                user_count = _seed_users(connection, archive)
                movie_count = _seed_movies(connection, archive)
                rating_count = _seed_ratings(connection, archive)
            tag_count = _seed_tags(connection, archive)
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
        "tags": tag_count,
    }


if __name__ == "__main__":
    result = import_movielens()
    print(
        "Imported MovieLens-1M into %(db_path)s: "
        "%(users)s users, %(movies)s movies, %(ratings)s ratings, %(tags)s tags" % result
    )

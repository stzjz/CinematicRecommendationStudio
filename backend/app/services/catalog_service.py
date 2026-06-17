from datetime import datetime
import math
import sqlite3
import time

from app.movie_metadata import occupation_label_for_user, summary_for_movie
from app.poster_catalog import poster_url_for_movie


class CatalogService(object):
    def __init__(self, users, movies, ratings, movie_tags, model_metrics, ablation_results, data_source="memory", db_path=None):
        self.users = users
        self.movies = [self._with_real_poster(movie) for movie in movies]
        self.ratings = ratings
        self.movie_tags = movie_tags
        self.model_metrics = model_metrics
        self.ablation_results = ablation_results
        self.data_source = data_source
        self.db_path = db_path
        self.movie_map = dict((movie["movie_id"], movie) for movie in self.movies)
        self.user_map = dict((user["user_id"], user) for user in users)
        self.ratings_by_user = {}
        self.ratings_by_movie = {}
        self.movie_rating_stats = {}
        for rating in self.ratings:
            self.ratings_by_user.setdefault(rating["user_id"], []).append(rating)
            self.ratings_by_movie.setdefault(rating["movie_id"], []).append(rating)
            stats = self.movie_rating_stats.setdefault(rating["movie_id"], {"total": 0.0, "count": 0})
            stats["total"] += float(rating["rating"])
            stats["count"] += 1
        self.tags_by_user = {}
        self.tags_by_movie = {}
        for tag in self.movie_tags:
            self.tags_by_user.setdefault(tag["user_id"], []).append(tag)
            self.tags_by_movie.setdefault(tag["movie_id"], []).append(tag)
        self.user_genre_vectors = {}

    def list_users(self, limit=None):
        if self.db_path:
            sql = "SELECT user_id, username, age, gender, occupation FROM users ORDER BY user_id DESC"
            params = ()
            if limit is not None:
                sql += " LIMIT ?"
                params = (limit,)
            with self._connect() as connection:
                rows = connection.execute(sql, params).fetchall()
            return [self._display_user(dict(row)) for row in rows]
        if limit is None:
            return self.users
        return list(reversed(self.users[-limit:]))

    def create_user(self, username, age=None, gender=None, occupation=None):
        clean_username = (username or "").strip()
        if not clean_username:
            raise ValueError("username is required")

        user = {
            "user_id": self._next_user_id(),
            "username": clean_username,
            "age": age,
            "gender": (gender or "").strip() or None,
            "occupation": (occupation or "").strip() or None,
        }
        if self.db_path:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO users (user_id, username, age, gender, occupation)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user["user_id"], user["username"], user["age"], user["gender"], user["occupation"]),
                )
                connection.commit()

        self.users.append(user)
        self.user_map[user["user_id"]] = user
        return self._display_user(user)

    def _next_user_id(self):
        if self.db_path:
            with self._connect() as connection:
                row = connection.execute("SELECT COALESCE(MAX(user_id), 0) + 1 AS next_id FROM users").fetchone()
                return int(row["next_id"])
        return max([user["user_id"] for user in self.users] or [0]) + 1

    def _with_real_poster(self, movie):
        item = dict(movie)
        item["poster_url"] = poster_url_for_movie(item.get("title"), item.get("year"), item.get("poster_url"))
        item["summary"] = summary_for_movie(item.get("title"), item.get("year"), item.get("summary"))
        return item

    def _display_user(self, user):
        item = dict(user)
        item["occupation"] = occupation_label_for_user(item.get("user_id"), item.get("occupation"))
        return item

    def _occupation_for_user(self, user_id, occupation):
        return occupation_label_for_user(user_id, occupation)

    def list_hot_movies(self, limit=10):
        if self.db_path:
            return self._list_hot_movies_sql(limit)
        ranked = self._rank_movies_by_rating_count()
        results = []
        for item in ranked[:limit]:
            movie_item = dict(item["movie"])
            movie_item["rating_count"] = item["rating_count"]
            movie_item["average_rating"] = item["average_rating"]
            movie_item["popularity_score"] = item["rating_count"]
            results.append(movie_item)
        return results

    def list_hot_movie_boards(self, limit_per_genre=6, max_boards=8):
        if self.db_path:
            return self._list_hot_movie_boards_sql(limit_per_genre, max_boards)
        boards = {}
        for item in self._rank_movies_by_rating_count():
            movie = item["movie"]
            primary_genre = self._primary_genre(movie)
            board = boards.setdefault(primary_genre, {"genre": primary_genre, "total_ratings": 0, "items": []})
            board["total_ratings"] += item["rating_count"]
            if len(board["items"]) < limit_per_genre:
                movie_item = dict(movie)
                movie_item["rating_count"] = item["rating_count"]
                movie_item["average_rating"] = item["average_rating"]
                movie_item["popularity_score"] = item["rating_count"]
                board["items"].append(movie_item)

        ranked_boards = list(boards.values())
        ranked_boards.sort(key=lambda board: (-board["total_ratings"], board["genre"]))
        return ranked_boards[:max_boards]

    def _rank_movies_by_rating_count(self):
        ranked = []
        for movie_id, info in self.movie_rating_stats.items():
            movie = self.movie_map.get(movie_id)
            if not movie:
                continue
            average_rating = info["total"] / info["count"]
            ranked.append(
                {
                    "movie": movie,
                    "rating_count": info["count"],
                    "average_rating": average_rating,
                }
            )

        ranked.sort(key=lambda item: (-item["rating_count"], -item["average_rating"], item["movie"]["title"]))
        return ranked

    def _primary_genre(self, movie):
        genres = movie.get("genres") or []
        if not genres:
            return "Other"
        return genres[0]

    def get_movie(self, movie_id):
        return self.movie_map.get(movie_id)

    def search_movies(self, query, limit=20):
        text = (query or "").strip().lower()
        if not text:
            return []
        terms = [term for term in text.replace(":", " ").replace("-", " ").split() if term]
        results = []
        for movie in self.movies:
            haystack = "%s %s %s" % (movie.get("title", ""), movie.get("year") or "", " ".join(movie.get("genres") or []))
            normalized = haystack.lower()
            if text in normalized or all(term in normalized for term in terms):
                item = dict(movie)
                stats = self._movie_stat(movie["movie_id"])
                item["rating_count"] = stats["count"]
                item["average_rating"] = stats["average_rating"]
                results.append(item)
        results.sort(key=lambda item: (0 if text in item["title"].lower() else 1, -item.get("rating_count", 0), item["title"]))
        return results[:limit]

    def get_user_movie_rating(self, user_id, movie_id):
        if self.db_path:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT rating_id, user_id, movie_id, rating, rated_at, comment
                    FROM ratings
                    WHERE user_id = ? AND movie_id = ?
                    ORDER BY rating_id DESC
                    LIMIT 1
                    """,
                    (user_id, movie_id),
                ).fetchone()
            return dict(row) if row else None

        for row in reversed(self.ratings_by_user.get(user_id, [])):
            if row["movie_id"] == movie_id:
                return dict(row)
        return None

    def get_user_ratings_for_recommendation(self, user_id):
        if self.db_path:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT user_id, movie_id, rating, rated_at, comment
                    FROM ratings
                    WHERE user_id = ?
                    ORDER BY rating_id
                    """,
                    (user_id,),
                ).fetchall()
            return [dict(row) for row in rows]

        return [dict(row) for row in self.ratings_by_user.get(user_id, [])]

    def save_user_rating(self, user_id, movie_id, rating, comment=None):
        if user_id not in self.user_map:
            raise ValueError("User not found")
        if movie_id not in self.movie_map:
            raise ValueError("Movie not found")
        score = float(rating)
        if score < 0.5 or score > 5.0:
            raise ValueError("rating must be between 0.5 and 5.0")

        clean_comment = (comment or "").strip() or None
        rated_at = str(int(time.time()))
        existing = self.get_user_movie_rating(user_id, movie_id)

        if self.db_path:
            with self._connect() as connection:
                if existing:
                    connection.execute(
                        """
                        UPDATE ratings
                        SET rating = ?, comment = ?, rated_at = ?
                        WHERE rating_id = ?
                        """,
                        (score, clean_comment, rated_at, existing["rating_id"]),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO ratings (user_id, movie_id, rating, rated_at, comment)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (user_id, movie_id, score, rated_at, clean_comment),
                    )
                self._refresh_movie_rating_stat(connection, movie_id)
                connection.commit()

        self._upsert_memory_rating(user_id, movie_id, score, rated_at, clean_comment)
        return self.get_user_movie_rating(user_id, movie_id) or {
            "user_id": user_id,
            "movie_id": movie_id,
            "rating": score,
            "rated_at": rated_at,
            "comment": clean_comment,
        }

    def delete_user_rating(self, user_id, movie_id):
        existing = self.get_user_movie_rating(user_id, movie_id)
        if not existing:
            return False
        if self.db_path:
            with self._connect() as connection:
                connection.execute("DELETE FROM ratings WHERE rating_id = ?", (existing["rating_id"],))
                self._refresh_movie_rating_stat(connection, movie_id)
                connection.commit()
        self._delete_memory_rating(user_id, movie_id)
        return True

    def _refresh_movie_rating_stat(self, connection, movie_id):
        row = connection.execute(
            "SELECT COUNT(*) AS rating_count, AVG(rating) AS average_rating FROM ratings WHERE movie_id = ?",
            (movie_id,),
        ).fetchone()
        if row["rating_count"]:
            connection.execute(
                """
                INSERT INTO movie_rating_stats (movie_id, rating_count, average_rating)
                VALUES (?, ?, ?)
                ON CONFLICT(movie_id) DO UPDATE SET
                    rating_count = excluded.rating_count,
                    average_rating = excluded.average_rating
                """,
                (movie_id, row["rating_count"], row["average_rating"]),
            )
        else:
            connection.execute("DELETE FROM movie_rating_stats WHERE movie_id = ?", (movie_id,))

    def _upsert_memory_rating(self, user_id, movie_id, rating, rated_at, comment):
        self._delete_memory_rating(user_id, movie_id)
        row = {"user_id": user_id, "movie_id": movie_id, "rating": rating, "rated_at": rated_at, "comment": comment}
        self.ratings.append(row)
        self.ratings_by_user.setdefault(user_id, []).append(row)
        self.ratings_by_movie.setdefault(movie_id, []).append(row)
        self._rebuild_movie_stat(movie_id)
        self.user_genre_vectors.pop(user_id, None)

    def _delete_memory_rating(self, user_id, movie_id):
        self.ratings = [row for row in self.ratings if not (row["user_id"] == user_id and row["movie_id"] == movie_id)]
        self.ratings_by_user[user_id] = [row for row in self.ratings_by_user.get(user_id, []) if row["movie_id"] != movie_id]
        self.ratings_by_movie[movie_id] = [row for row in self.ratings_by_movie.get(movie_id, []) if row["user_id"] != user_id]
        self._rebuild_movie_stat(movie_id)
        self.user_genre_vectors.pop(user_id, None)

    def _rebuild_movie_stat(self, movie_id):
        rows = self.ratings_by_movie.get(movie_id, [])
        if rows:
            self.movie_rating_stats[movie_id] = {"total": sum(row["rating"] for row in rows), "count": len(rows)}
        else:
            self.movie_rating_stats.pop(movie_id, None)

    def _movie_stat(self, movie_id):
        if self.db_path:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT rating_count, average_rating FROM movie_rating_stats WHERE movie_id = ?",
                    (movie_id,),
                ).fetchone()
            if row:
                return {"count": row["rating_count"], "average_rating": row["average_rating"]}
            return {"count": 0, "average_rating": None}
        stats = self.movie_rating_stats.get(movie_id)
        if not stats:
            return {"count": 0, "average_rating": None}
        return {"count": stats["count"], "average_rating": stats["total"] / stats["count"]}

    def get_movie_detail(self, movie_id):
        if self.db_path:
            return self._get_movie_detail_sql(movie_id)
        movie = self.get_movie(movie_id)
        if not movie:
            return None

        movie_ratings = self.ratings_by_movie.get(movie_id, [])
        average_rating = None
        if movie_ratings:
            average_rating = sum(row["rating"] for row in movie_ratings) / len(movie_ratings)

        detail = dict(movie)
        detail["detail_tags"] = self._build_detail_tags(movie)
        detail["average_rating"] = average_rating
        detail["rating_count"] = len(movie_ratings)
        detail["rating_distribution"] = self._build_rating_distribution(movie_ratings)
        detail["rating_records"] = self._build_movie_rating_records(movie, movie_ratings, limit=120)
        detail["comment_samples"] = self._build_comment_samples(movie, movie_ratings)
        detail["user_tags"] = self._build_user_tag_summary(movie_id)
        return detail

    def get_movie_rating_records(self, movie_id, limit=8, offset=0):
        movie = self.get_movie(movie_id)
        if not movie:
            return None
        if self.db_path:
            with self._connect() as connection:
                total_row = connection.execute(
                    "SELECT COUNT(*) AS total FROM ratings WHERE movie_id = ?",
                    (movie_id,),
                ).fetchone()
                rows = connection.execute(
                    """
                    SELECT r.user_id, r.rating, r.rated_at, r.comment, u.username, u.occupation
                    FROM ratings r
                    LEFT JOIN users u ON u.user_id = r.user_id
                    WHERE r.movie_id = ?
                    ORDER BY CAST(COALESCE(r.rated_at, '0') AS INTEGER) DESC, r.user_id
                    LIMIT ? OFFSET ?
                    """,
                    (movie_id, limit, offset),
                ).fetchall()
            items = [
                {
                    "record_id": "%s-%s" % (movie_id, row["user_id"]),
                    "user_id": row["user_id"],
                    "username": row["username"] or "user-%s" % row["user_id"],
                    "occupation": self._occupation_for_user(row["user_id"], row["occupation"]),
                    "rating": row["rating"],
                    "rated_at": self._format_rating_date(row["rated_at"], offset + index),
                    "comment": row["comment"],
                }
                for index, row in enumerate(rows)
            ]
            return {"items": items, "total": int(total_row["total"] or 0)}

        movie_ratings = self.ratings_by_movie.get(movie_id, [])
        sorted_ratings = sorted(movie_ratings, key=lambda item: (-self._timestamp_value(item.get("rated_at")), item["user_id"]))
        return {
            "items": self._build_movie_rating_records(movie, sorted_ratings[offset : offset + limit], limit=limit, base_index=offset),
            "total": len(sorted_ratings),
        }

    def get_user_history(self, user_id):
        if self.db_path:
            return self._get_user_history_sql(user_id)
        history = list(self.ratings_by_user.get(user_id, []))
        history.sort(key=lambda row: (-self._timestamp_value(row.get("rated_at")), -row["rating"], row["movie_id"]))
        results = []
        for row in history:
            movie = self.movie_map.get(row["movie_id"])
            if movie:
                item = dict(movie)
                item["rating"] = row["rating"]
                results.append(item)
        return results

    def get_user_preference_profile(self, user_id, window="all"):
        if self.db_path:
            return self._get_user_preference_profile_sql(user_id, window)
        all_history = list(self.ratings_by_user.get(user_id, []))
        selected_history = self._filter_ratings_by_window(all_history, window)
        if not selected_history and window != "all":
            selected_history = all_history

        selected_history.sort(key=lambda row: (-self._timestamp_value(row.get("rated_at")), row["movie_id"]))
        rated_movie_ids = set(row["movie_id"] for row in selected_history)
        top_movie_items = []
        for row in selected_history[:8]:
            movie = self.movie_map.get(row["movie_id"])
            if not movie:
                continue
            top_movie_items.append(
                {
                    "movie_id": movie["movie_id"],
                    "title": movie["title"],
                    "genres": movie.get("genres") or [],
                    "rating": row["rating"],
                    "rated_at": self._format_rating_date(row.get("rated_at"), 0),
                }
            )

        genre_scores = self._build_genre_vector(selected_history)

        genres = []
        for info in genre_scores.values():
            genres.append(
                {
                    "label": info["label"],
                    "count": info["count"],
                    "score": round(info["score"], 3),
                    "average_rating": info["rating_total"] / info["count"],
                }
            )
        genres.sort(key=lambda item: (-item["score"], -item["count"], item["label"]))

        authored_tags = self._summarize_user_tags(user_id, window)
        movie_tags = self._summarize_tags_for_movies(rated_movie_ids)
        similar_users = self._find_similar_users(user_id, genre_scores, rated_movie_ids, limit=5)
        window_info = self._resolve_window(window, all_history)

        return {
            "user_id": user_id,
            "window": window_info,
            "rating_count": len(selected_history),
            "rated_movie_count": len(rated_movie_ids),
            "rating_distribution": self._build_exact_rating_distribution(selected_history),
            "genres": genres[:8],
            "authored_tags": authored_tags[:16],
            "movie_tags": movie_tags[:20],
            "similar_users": similar_users,
            "top_history": top_movie_items,
            "interaction_graph": self._build_interaction_graph(user_id, selected_history, top_movie_items, similar_users),
            "director_status": {
                "available": False,
                "reason": "MovieLens 10M only includes movie title, release year, genres, ratings, timestamps, and user-supplied tags; it does not include director metadata.",
            },
        }

    def get_model_metrics(self):
        return self.model_metrics

    def get_ablation_results(self):
        return self.ablation_results

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _list_hot_movies_sql(self, limit):
        query = """
        SELECT movie_id, rating_count, average_rating
        FROM movie_rating_stats
        ORDER BY rating_count DESC, average_rating DESC
        LIMIT ?
        """
        with self._connect() as connection:
            rows = connection.execute(query, (limit,)).fetchall()
        return [self._movie_with_stats(row["movie_id"], row["rating_count"], row["average_rating"]) for row in rows if self.movie_map.get(row["movie_id"])]

    def _list_hot_movie_boards_sql(self, limit_per_genre, max_boards):
        query = """
        SELECT movie_id, rating_count, average_rating
        FROM movie_rating_stats
        ORDER BY rating_count DESC, average_rating DESC
        LIMIT 5000
        """
        with self._connect() as connection:
            rows = connection.execute(query).fetchall()

        boards = {}
        for row in rows:
            movie = self.movie_map.get(row["movie_id"])
            if not movie:
                continue
            primary_genre = self._primary_genre(movie)
            board = boards.setdefault(primary_genre, {"genre": primary_genre, "total_ratings": 0, "items": []})
            board["total_ratings"] += row["rating_count"]
            if len(board["items"]) < limit_per_genre:
                board["items"].append(self._movie_with_stats(row["movie_id"], row["rating_count"], row["average_rating"]))

        ranked_boards = list(boards.values())
        ranked_boards.sort(key=lambda board: (-board["total_ratings"], board["genre"]))
        return ranked_boards[:max_boards]

    def _movie_with_stats(self, movie_id, rating_count, average_rating):
        movie_item = dict(self.movie_map[movie_id])
        movie_item["rating_count"] = int(rating_count or 0)
        movie_item["average_rating"] = float(average_rating or 0)
        movie_item["popularity_score"] = int(rating_count or 0)
        return movie_item

    def _get_movie_detail_sql(self, movie_id):
        movie = self.get_movie(movie_id)
        if not movie:
            return None
        with self._connect() as connection:
            summary = connection.execute(
                "SELECT COUNT(*) AS rating_count, AVG(rating) AS average_rating FROM ratings WHERE movie_id = ?",
                (movie_id,),
            ).fetchone()
            distribution_rows = connection.execute(
                """
                SELECT CAST(ROUND(rating) AS INTEGER) AS rating_bucket, COUNT(*) AS count
                FROM ratings
                WHERE movie_id = ?
                GROUP BY rating_bucket
                """,
                (movie_id,),
            ).fetchall()
            record_rows = connection.execute(
                """
                SELECT r.user_id, r.rating, r.rated_at, r.comment, u.username, u.occupation
                FROM ratings r
                LEFT JOIN users u ON u.user_id = r.user_id
                WHERE r.movie_id = ?
                ORDER BY CAST(COALESCE(r.rated_at, '0') AS INTEGER) DESC, r.user_id
                LIMIT 120
                """,
                (movie_id,),
            ).fetchall()
            sample_rows = {
                "high": connection.execute(self._comment_sample_query("rating >= 4"), (movie_id,)).fetchall(),
                "medium": connection.execute(self._comment_sample_query("rating >= 2.5 AND rating < 4"), (movie_id,)).fetchall(),
                "low": connection.execute(self._comment_sample_query("rating < 2.5"), (movie_id,)).fetchall(),
            }

        distribution_map = dict((int(row["rating_bucket"]), row["count"]) for row in distribution_rows)
        detail = dict(movie)
        detail["detail_tags"] = self._build_detail_tags(movie)
        detail["average_rating"] = float(summary["average_rating"]) if summary and summary["average_rating"] is not None else None
        detail["rating_count"] = int(summary["rating_count"] or 0) if summary else 0
        detail["rating_distribution"] = [{"rating": score, "count": int(distribution_map.get(score, 0))} for score in [5, 4, 3, 2, 1]]
        detail["rating_records"] = [
            {
                "record_id": "%s-%s" % (movie_id, row["user_id"]),
                "user_id": row["user_id"],
                "username": row["username"] or "user-%s" % row["user_id"],
                "occupation": self._occupation_for_user(row["user_id"], row["occupation"]),
                "rating": row["rating"],
                "rated_at": self._format_rating_date(row["rated_at"], index),
                "comment": row["comment"],
            }
            for index, row in enumerate(record_rows)
        ]
        detail["comment_samples"] = {
            key: [
                {
                    "record_id": "%s-%s-%s" % (movie_id, key, row["user_id"]),
                    "user_id": row["user_id"],
                    "username": row["username"] or "user-%s" % row["user_id"],
                    "occupation": self._occupation_for_user(row["user_id"], row["occupation"]),
                    "rating": row["rating"],
                    "rated_at": self._format_rating_date(row["rated_at"], index),
                    "comment": row["comment"],
                }
                for index, row in enumerate(rows)
            ]
            for key, rows in sample_rows.items()
        }
        detail["user_tags"] = self._build_user_tag_summary(movie_id)
        return detail

    def _comment_sample_query(self, rating_clause):
        return """
            SELECT r.user_id, r.rating, r.rated_at, r.comment, u.username, u.occupation
            FROM ratings r
            LEFT JOIN users u ON u.user_id = r.user_id
            WHERE r.movie_id = ? AND %s
            ORDER BY
              CASE WHEN r.comment IS NOT NULL AND TRIM(r.comment) != '' THEN 0 ELSE 1 END,
              CAST(COALESCE(r.rated_at, '0') AS INTEGER) DESC,
              r.user_id
            LIMIT 2
        """ % rating_clause

    def _get_user_history_sql(self, user_id):
        query = """
        SELECT movie_id, rating, rated_at, comment
        FROM ratings
        WHERE user_id = ?
        ORDER BY CAST(COALESCE(rated_at, '0') AS INTEGER) DESC, rating DESC, movie_id
        LIMIT 200
        """
        with self._connect() as connection:
            rows = connection.execute(query, (user_id,)).fetchall()
        return self._history_rows_to_movies(rows)

    def _get_user_preference_profile_sql(self, user_id, window):
        with self._connect() as connection:
            all_rows = connection.execute(
                """
                SELECT movie_id, rating, rated_at
                FROM ratings
                WHERE user_id = ?
                ORDER BY CAST(COALESCE(rated_at, '0') AS INTEGER) DESC, movie_id
                """,
                (user_id,),
            ).fetchall()
        all_history = [dict(row) for row in all_rows]
        selected_history = self._filter_ratings_by_window(all_history, window)
        if not selected_history and window != "all":
            selected_history = all_history
        selected_history.sort(key=lambda row: (-self._timestamp_value(row.get("rated_at")), row["movie_id"]))
        rated_movie_ids = set(row["movie_id"] for row in selected_history)
        genre_scores = self._build_genre_vector(selected_history)

        genres = []
        for info in genre_scores.values():
            genres.append(
                {
                    "label": info["label"],
                    "count": info["count"],
                    "score": round(info["score"], 3),
                    "average_rating": info["rating_total"] / info["count"],
                }
            )
        genres.sort(key=lambda item: (-item["score"], -item["count"], item["label"]))

        movie_tags = self._summarize_tags_for_movies(rated_movie_ids)
        authored_tags = self._summarize_user_tags(user_id, window)
        top_movie_items = self._history_rows_to_movies(selected_history[:8])

        return {
            "user_id": user_id,
            "window": self._resolve_window(window, all_history),
            "rating_count": len(selected_history),
            "rated_movie_count": len(rated_movie_ids),
            "rating_distribution": self._build_exact_rating_distribution(selected_history),
            "genres": genres[:8],
            "authored_tags": authored_tags[:16],
            "movie_tags": movie_tags[:20],
            "similar_users": self._find_similar_users_sql(user_id, genre_scores, rated_movie_ids, limit=5),
            "top_history": top_movie_items,
            "interaction_graph": self._build_interaction_graph_sql(user_id, selected_history, top_movie_items),
            "director_status": {
                "available": False,
                "reason": "MovieLens 10M only includes movie title, release year, genres, ratings, timestamps, and user-supplied tags; it does not include director metadata.",
            },
        }

    def _history_rows_to_movies(self, rows):
        results = []
        for row in rows:
            movie = self.movie_map.get(row["movie_id"])
            if movie:
                item = dict(movie)
                item["rating"] = row["rating"]
                item["rated_at"] = self._format_rating_date(self._row_value(row, "rated_at"), 0)
                item["comment"] = self._row_value(row, "comment")
                results.append(item)
        return results

    def _build_interaction_graph_sql(self, user_id, selected_history, top_movie_items):
        seed_movies = top_movie_items[:5]
        seed_ids = [movie["movie_id"] for movie in seed_movies]
        if not seed_ids:
            return {"nodes": [], "edges": []}

        placeholders = ",".join("?" for _ in seed_ids)
        with self._connect() as connection:
            neighbor_rows = connection.execute(
                """
                SELECT r.user_id, u.username, u.occupation, COUNT(*) AS overlap_count, AVG(r.rating) AS avg_rating
                FROM ratings r
                LEFT JOIN users u ON u.user_id = r.user_id
                WHERE r.movie_id IN (%s) AND r.user_id != ?
                GROUP BY r.user_id
                ORDER BY overlap_count DESC, avg_rating DESC, r.user_id
                LIMIT 4
                """ % placeholders,
                tuple(seed_ids + [user_id]),
            ).fetchall()
            neighbor_ids = [row["user_id"] for row in neighbor_rows]
            edge_rows = []
            candidate_rows = []
            if neighbor_ids:
                neighbor_placeholders = ",".join("?" for _ in neighbor_ids)
                edge_rows = connection.execute(
                    """
                    SELECT user_id, movie_id, rating
                    FROM ratings
                    WHERE user_id IN (%s) AND movie_id IN (%s)
                    """ % (neighbor_placeholders, placeholders),
                    tuple(neighbor_ids + seed_ids),
                ).fetchall()
                candidate_rows = connection.execute(
                    """
                    SELECT r.movie_id, COUNT(*) AS support, AVG(r.rating) AS avg_rating
                    FROM ratings r
                    WHERE r.user_id IN (%s) AND r.movie_id NOT IN (%s)
                    GROUP BY r.movie_id
                    ORDER BY support DESC, avg_rating DESC, r.movie_id
                    LIMIT 8
                    """ % (neighbor_placeholders, placeholders),
                    tuple(neighbor_ids + seed_ids),
                ).fetchall()

        nodes = [{"id": "u-%s" % user_id, "type": "target_user", "label": "当前用户", "subtitle": "user %s" % user_id}]
        edges = []
        for movie in seed_movies:
            movie_node = "m-%s" % movie["movie_id"]
            nodes.append({"id": movie_node, "type": "history_movie", "label": movie["title"], "subtitle": "%.1f 分" % float(movie.get("rating") or 0)})
            edges.append({"source": "u-%s" % user_id, "target": movie_node, "label": "历史评分"})

        for row in neighbor_rows:
            nodes.append(
                {
                    "id": "n-%s" % row["user_id"],
                    "type": "neighbor_user",
                    "label": row["username"] or "user-%s" % row["user_id"],
                    "subtitle": "%s 个共同电影" % row["overlap_count"],
                    "occupation": self._occupation_for_user(row["user_id"], row["occupation"]),
                }
            )
        for row in edge_rows:
            edges.append({"source": "m-%s" % row["movie_id"], "target": "n-%s" % row["user_id"], "label": "%.1f" % float(row["rating"])})

        for row in candidate_rows:
            movie = self.movie_map.get(row["movie_id"])
            if not movie:
                continue
            candidate_node = "c-%s" % row["movie_id"]
            nodes.append(
                {
                    "id": candidate_node,
                    "type": "candidate_movie",
                    "label": movie["title"],
                    "subtitle": "%s 个邻居 · %.1f 分" % (row["support"], float(row["avg_rating"] or 0)),
                }
            )
            for neighbor_id in neighbor_ids[:3]:
                edges.append({"source": "n-%s" % neighbor_id, "target": candidate_node, "label": "传播"})

        return {"nodes": nodes, "edges": edges}

    def _build_interaction_graph(self, user_id, selected_history, top_movie_items, similar_users):
        seed_movies = top_movie_items[:5]
        seed_ids = [movie["movie_id"] for movie in seed_movies]
        if not seed_ids:
            return {"nodes": [], "edges": []}
        neighbor_ids = [user["user_id"] for user in similar_users[:4]]
        nodes = [{"id": "u-%s" % user_id, "type": "target_user", "label": "当前用户", "subtitle": "user %s" % user_id}]
        edges = []
        for movie in seed_movies:
            movie_node = "m-%s" % movie["movie_id"]
            nodes.append({"id": movie_node, "type": "history_movie", "label": movie["title"], "subtitle": "%.1f 分" % float(movie.get("rating") or 0)})
            edges.append({"source": "u-%s" % user_id, "target": movie_node, "label": "历史评分"})
        for user in similar_users[:4]:
            neighbor_node = "n-%s" % user["user_id"]
            nodes.append({"id": neighbor_node, "type": "neighbor_user", "label": user["username"], "subtitle": "%s 条评分" % user.get("rating_count", 0)})
            for movie_id in seed_ids[:2]:
                edges.append({"source": "m-%s" % movie_id, "target": neighbor_node, "label": "共同"})
        candidates = []
        for neighbor_id in neighbor_ids:
            for row in self.ratings_by_user.get(neighbor_id, [])[:20]:
                if row["movie_id"] not in seed_ids and row["movie_id"] in self.movie_map:
                    candidates.append(row["movie_id"])
        for movie_id in list(dict.fromkeys(candidates))[:5]:
            movie = self.movie_map[movie_id]
            candidate_node = "c-%s" % movie_id
            nodes.append({"id": candidate_node, "type": "candidate_movie", "label": movie["title"], "subtitle": "邻居候选"})
            for neighbor_id in neighbor_ids[:3]:
                edges.append({"source": "n-%s" % neighbor_id, "target": candidate_node, "label": "传播"})
        return {"nodes": nodes, "edges": edges}

    def _row_value(self, row, key, default=None):
        if hasattr(row, "keys") and key in row.keys():
            return row[key]
        if isinstance(row, dict):
            return row.get(key, default)
        return default

    def _find_similar_users_sql(self, user_id, genre_scores, rated_movie_ids, limit=5):
        if not genre_scores or not rated_movie_ids:
            return []
        placeholders = ",".join("?" for _ in rated_movie_ids)
        params = list(rated_movie_ids) + [user_id]
        query = """
        SELECT r.user_id, COUNT(*) AS overlap_count
        FROM ratings r
        WHERE r.movie_id IN (%s) AND r.user_id != ?
        GROUP BY r.user_id
        ORDER BY overlap_count DESC
        LIMIT 80
        """ % placeholders
        with self._connect() as connection:
            candidate_rows = connection.execute(query, params).fetchall()

        target = dict((genre, info["score"]) for genre, info in genre_scores.items())
        target_norm = math.sqrt(sum(value * value for value in target.values()))
        candidates = []
        for candidate in candidate_rows:
            other_user_id = candidate["user_id"]
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT movie_id, rating FROM ratings WHERE user_id = ?",
                    (other_user_id,),
                ).fetchall()
            other_vector = self._build_genre_vector([dict(row) for row in rows])
            dot = sum(target.get(genre, 0.0) * info.get("score", 0.0) for genre, info in other_vector.items())
            other_norm = math.sqrt(sum(info.get("score", 0.0) * info.get("score", 0.0) for info in other_vector.values()))
            if not dot or not other_norm or not target_norm:
                continue
            profile = self.user_map.get(other_user_id, {})
            candidates.append(
                {
                    "user_id": other_user_id,
                    "username": profile.get("username", "movielens-%s" % other_user_id),
                    "occupation": self._occupation_for_user(other_user_id, profile.get("occupation")),
                    "similarity": round(dot / (target_norm * other_norm), 3),
                    "rating_count": len(rows),
                }
            )
        candidates.sort(key=lambda item: (-item["similarity"], -item["rating_count"], item["user_id"]))
        return candidates[:limit]

    def _build_detail_tags(self, movie):
        tags = []
        for genre in movie.get("genres") or []:
            tags.append({"label": genre, "type": "genre"})
        if movie.get("year"):
            tags.append({"label": str(movie["year"]), "type": "year"})
        if movie.get("summary"):
            tags.append({"label": "has-summary", "type": "metadata"})
        return tags

    def _build_rating_distribution(self, movie_ratings):
        buckets = []
        for score in [5, 4, 3, 2, 1]:
            count = 0
            for row in movie_ratings:
                if int(round(row["rating"])) == score:
                    count += 1
            buckets.append({"rating": score, "count": count})
        return buckets

    def _build_exact_rating_distribution(self, ratings):
        scores = [5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5]
        counts = dict((score, 0) for score in scores)
        for row in ratings:
            score = round(float(row["rating"]) * 2) / 2
            if score in counts:
                counts[score] += 1
        return [{"rating": score, "label": "%.1f" % score, "count": counts[score]} for score in scores]

    def _build_user_tag_summary(self, movie_id):
        aggregates = {}
        for row in self.tags_by_movie.get(movie_id, []):
            tag = (row.get("tag") or "").strip()
            if not tag:
                continue
            key = tag.lower()
            info = aggregates.setdefault(key, {"tag": tag, "count": 0, "users": set(), "latest_tagged_at": None})
            info["count"] += 1
            info["users"].add(row["user_id"])
            tagged_at = self._format_rating_date(row.get("tagged_at"), 0)
            if tagged_at and (info["latest_tagged_at"] is None or tagged_at > info["latest_tagged_at"]):
                info["latest_tagged_at"] = tagged_at

        tags = []
        for info in aggregates.values():
            tags.append(
                {
                    "tag": info["tag"],
                    "count": info["count"],
                    "user_count": len(info["users"]),
                    "latest_tagged_at": info["latest_tagged_at"],
                }
            )
        tags.sort(key=lambda item: (-item["count"], item["tag"].lower()))
        return tags[:40]

    def _build_movie_rating_records(self, movie, movie_ratings, limit=24, base_index=0, presorted=False):
        records = []
        sorted_ratings = list(movie_ratings) if presorted else sorted(movie_ratings, key=lambda item: (-self._timestamp_value(item.get("rated_at")), item["user_id"]))
        for index, row in enumerate(sorted_ratings[:limit]):
            user = self.user_map.get(row["user_id"], {})
            records.append(
                {
                    "record_id": "%s-%s" % (movie["movie_id"], row["user_id"]),
                    "user_id": row["user_id"],
                    "username": user.get("username", "user-%s" % row["user_id"]),
                    "occupation": user.get("occupation"),
                    "rating": row["rating"],
                    "rated_at": self._format_rating_date(row.get("rated_at"), base_index + index),
                    "comment": row.get("comment"),
                }
            )
        return records

    def _build_comment_samples(self, movie, movie_ratings):
        bands = {
            "high": lambda rating: rating >= 4,
            "medium": lambda rating: 2.5 <= rating < 4,
            "low": lambda rating: rating < 2.5,
        }
        samples = {}
        for key, predicate in bands.items():
            rows = [row for row in movie_ratings if predicate(float(row["rating"]))]
            rows.sort(
                key=lambda row: (
                    0 if (row.get("comment") or "").strip() else 1,
                    -self._timestamp_value(row.get("rated_at")),
                    row["user_id"],
                )
            )
            samples[key] = self._build_movie_rating_records(movie, rows, limit=2, presorted=True)
        return samples

    def _summarize_user_tags(self, user_id, window):
        tag_rows = self._filter_tags_by_window(list(self.tags_by_user.get(user_id, [])), window)
        return self._summarize_tag_rows(tag_rows)

    def _summarize_tags_for_movies(self, movie_ids):
        rows = []
        for movie_id in movie_ids:
            rows.extend(self.tags_by_movie.get(movie_id, []))
        return self._summarize_tag_rows(rows)

    def _summarize_tag_rows(self, rows):
        aggregates = {}
        for row in rows:
            tag = (row.get("tag") or "").strip()
            if not tag:
                continue
            key = tag.lower()
            info = aggregates.setdefault(key, {"tag": tag, "count": 0, "users": set()})
            info["count"] += 1
            info["users"].add(row.get("user_id"))

        results = []
        for info in aggregates.values():
            results.append({"tag": info["tag"], "count": info["count"], "user_count": len(info["users"])})
        results.sort(key=lambda item: (-item["count"], item["tag"].lower()))
        return results

    def _find_similar_users(self, user_id, genre_scores, rated_movie_ids, limit=5):
        if not genre_scores:
            return []

        target = dict((genre, info["score"]) for genre, info in genre_scores.items())
        target_norm = math.sqrt(sum(value * value for value in target.values()))
        if not target_norm:
            return []

        candidate_overlap = {}
        for movie_id in rated_movie_ids:
            for row in self.ratings_by_movie.get(movie_id, []):
                other_user_id = row["user_id"]
                if other_user_id == user_id:
                    continue
                candidate_overlap[other_user_id] = candidate_overlap.get(other_user_id, 0) + 1
        candidate_ids = sorted(candidate_overlap, key=lambda item: (-candidate_overlap[item], item))[:400]

        candidates = []
        for other_user_id in candidate_ids:
            if other_user_id == user_id:
                continue
            ratings = self.ratings_by_user.get(other_user_id, [])
            other_vector = self._get_user_genre_vector(other_user_id)
            dot = sum(target.get(genre, 0.0) * info.get("score", 0.0) for genre, info in other_vector.items())
            other_norm = math.sqrt(sum(info.get("score", 0.0) * info.get("score", 0.0) for info in other_vector.values()))
            if not dot or not other_norm:
                continue
            profile = self.user_map.get(other_user_id, {})
            candidates.append(
                {
                    "user_id": other_user_id,
                    "username": profile.get("username", "user-%s" % other_user_id),
                    "occupation": self._occupation_for_user(other_user_id, profile.get("occupation")),
                    "similarity": dot / (target_norm * other_norm),
                    "rating_count": len(ratings),
                }
            )

        candidates.sort(key=lambda item: (-item["similarity"], -item["rating_count"], item["user_id"]))
        for item in candidates[:limit]:
            item["similarity"] = round(item["similarity"], 3)
        return candidates[:limit]

    def _get_user_genre_vector(self, user_id):
        if user_id not in self.user_genre_vectors:
            self.user_genre_vectors[user_id] = self._build_genre_vector(self.ratings_by_user.get(user_id, []))
        return self.user_genre_vectors[user_id]

    def _build_genre_vector(self, ratings):
        genre_scores = {}
        for row in ratings:
            movie = self.movie_map.get(row["movie_id"])
            if not movie:
                continue
            weight = max(float(row["rating"]) - 2.5, 0.5)
            for genre in movie.get("genres") or []:
                info = genre_scores.setdefault(genre, {"label": genre, "count": 0, "score": 0.0, "rating_total": 0.0})
                info["count"] += 1
                info["score"] += weight
                info["rating_total"] += float(row["rating"])
        return genre_scores

    def _filter_ratings_by_window(self, rows, window):
        window_info = self._resolve_window(window, rows)
        since = window_info.get("since_ts")
        if since is None:
            return list(rows)
        return [row for row in rows if self._timestamp_value(row.get("rated_at")) >= since]

    def _filter_tags_by_window(self, rows, window):
        window_info = self._resolve_window(window, rows, field_name="tagged_at")
        since = window_info.get("since_ts")
        if since is None:
            return list(rows)
        return [row for row in rows if self._timestamp_value(row.get("tagged_at")) >= since]

    def _resolve_window(self, window, rows, field_name="rated_at"):
        value = window or "all"
        labels = {
            "all": "全部历史",
            "year": "近一年",
            "quarter": "近90天",
            "month": "近30天",
        }
        days_by_window = {"year": 365, "quarter": 90, "month": 30}
        latest_ts = max([self._timestamp_value(row.get(field_name)) for row in rows] or [0])
        since_ts = None
        if value in days_by_window and latest_ts:
            since_ts = latest_ts - days_by_window[value] * 86400
        elif value not in labels:
            value = "all"
        return {
            "key": value,
            "label": labels.get(value, "全部历史"),
            "latest_date": self._format_rating_date(latest_ts, 0) if latest_ts else None,
            "since_date": self._format_rating_date(since_ts, 0) if since_ts else None,
            "since_ts": since_ts,
        }

    def _fallback_rating_date(self, index):
        return "2026-05-%02d" % (12 + (index % 18))

    def _format_rating_date(self, raw_value, index):
        if not raw_value:
            return self._fallback_rating_date(index)
        value = str(raw_value)
        if value.isdigit():
            return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d")
        return value

    def _timestamp_value(self, raw_value):
        if not raw_value:
            return 0
        value = str(raw_value)
        if value.isdigit():
            return int(value)
        try:
            return int(datetime.strptime(value[:10], "%Y-%m-%d").timestamp())
        except ValueError:
            return 0

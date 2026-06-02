from .base import BaseRecommender


class PopularityRecommender(BaseRecommender):
    name = "popularity"
    description = "Popularity baseline using average rating and rating count"

    def __init__(self, movies, ratings):
        self.movies = movies
        self.ratings = ratings
        self.movie_map = dict((movie["movie_id"], movie) for movie in movies)
        self.user_seen = {}
        self.movie_stats = {}
        self._build_indexes()

    def _build_indexes(self):
        for rating in self.ratings:
            self.user_seen.setdefault(rating["user_id"], set()).add(rating["movie_id"])
            stats = self.movie_stats.setdefault(rating["movie_id"], {"total": 0.0, "count": 0})
            stats["total"] += rating["rating"]
            stats["count"] += 1

    def recommend(self, user_id, limit):
        seen = self.user_seen.get(user_id, set())
        candidates = []
        for movie_id, stats in self.movie_stats.items():
            if movie_id in seen:
                continue
            score = stats["total"] / stats["count"]
            candidates.append((score, stats["count"], movie_id))

        candidates.sort(key=lambda item: (-item[0], -item[1], self.movie_map[item[2]]["title"]))
        results = []
        for score, count, movie_id in candidates[:limit]:
            movie = dict(self.movie_map[movie_id])
            movie["score"] = round(score, 4)
            movie["reason"] = "这部电影在全站用户中整体评分较高"
            movie["support"] = count
            results.append(movie)
        return results

    def record_rating(self, user_id, movie_id, rating):
        if movie_id in self.user_seen.get(user_id, set()):
            return
        self.user_seen.setdefault(user_id, set()).add(movie_id)
        stats = self.movie_stats.setdefault(movie_id, {"total": 0.0, "count": 0})
        stats["total"] += float(rating)
        stats["count"] += 1

    def delete_rating(self, user_id, movie_id):
        self.user_seen.get(user_id, set()).discard(movie_id)

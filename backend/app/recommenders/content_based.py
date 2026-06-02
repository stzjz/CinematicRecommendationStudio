from .base import BaseRecommender


class ContentBasedRecommender(BaseRecommender):
    name = "content_based"
    description = "Content-based baseline using favorite genre preference"

    def __init__(self, movies, ratings):
        self.movies = movies
        self.ratings = ratings
        self.movie_map = dict((movie["movie_id"], movie) for movie in movies)
        self.user_ratings = {}
        self._build_indexes()

    def _build_indexes(self):
        for row in self.ratings:
            self.user_ratings.setdefault(row["user_id"], {})[row["movie_id"]] = row["rating"]

    def _build_genre_profile(self, user_id):
        profile = {}
        for movie_id, rating in self.user_ratings.get(user_id, {}).items():
            if rating < 4.0:
                continue
            movie = self.movie_map.get(movie_id)
            if not movie:
                continue
            for genre in movie["genres"]:
                profile[genre] = profile.get(genre, 0.0) + rating
        return profile

    def recommend(self, user_id, limit):
        seen = set(self.user_ratings.get(user_id, {}))
        profile = self._build_genre_profile(user_id)
        ranked = []

        for movie in self.movies:
            if movie["movie_id"] in seen:
                continue
            score = 0.0
            for genre in movie["genres"]:
                score += profile.get(genre, 0.0)
            if score <= 0:
                continue
            ranked.append((score, movie["movie_id"]))

        ranked.sort(key=lambda item: (-item[0], self.movie_map[item[1]]["title"]))
        results = []
        for score, movie_id in ranked[:limit]:
            movie = dict(self.movie_map[movie_id])
            movie["score"] = round(score, 4)
            movie["reason"] = "根据你偏好的电影类型进行推荐"
            results.append(movie)
        return results

    def record_rating(self, user_id, movie_id, rating):
        self.user_ratings.setdefault(user_id, {})[movie_id] = float(rating)

    def delete_rating(self, user_id, movie_id):
        self.user_ratings.get(user_id, {}).pop(movie_id, None)

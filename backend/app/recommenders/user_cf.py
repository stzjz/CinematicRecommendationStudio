from .base import BaseRecommender


class UserCFRecommender(BaseRecommender):
    name = "user_cf"
    description = "User-based collaborative filtering baseline"

    def __init__(self, movies, ratings):
        self.movies = movies
        self.ratings = ratings
        self.movie_map = dict((movie["movie_id"], movie) for movie in movies)
        self.user_ratings = {}
        self._build_indexes()

    def _build_indexes(self):
        for row in self.ratings:
            self.user_ratings.setdefault(row["user_id"], {})[row["movie_id"]] = row["rating"]

    def _similarity(self, left_user, right_user):
        left = self.user_ratings.get(left_user, {})
        right = self.user_ratings.get(right_user, {})
        overlap = set(left) & set(right)
        if not overlap:
            return 0.0

        numerator = 0.0
        left_norm = 0.0
        right_norm = 0.0
        for movie_id in overlap:
            numerator += left[movie_id] * right[movie_id]
            left_norm += left[movie_id] * left[movie_id]
            right_norm += right[movie_id] * right[movie_id]

        if not left_norm or not right_norm:
            return 0.0
        return numerator / ((left_norm ** 0.5) * (right_norm ** 0.5))

    def recommend(self, user_id, limit):
        target_ratings = self.user_ratings.get(user_id, {})
        scores = {}
        supports = {}

        for other_user in self.user_ratings:
            if other_user == user_id:
                continue
            similarity = self._similarity(user_id, other_user)
            if similarity <= 0:
                continue
            for movie_id, rating in self.user_ratings[other_user].items():
                if movie_id in target_ratings:
                    continue
                scores[movie_id] = scores.get(movie_id, 0.0) + similarity * rating
                supports[movie_id] = supports.get(movie_id, 0.0) + similarity

        ranked = []
        for movie_id, score in scores.items():
            support = supports.get(movie_id, 0.0)
            if support <= 0:
                continue
            ranked.append((score / support, support, movie_id))

        ranked.sort(key=lambda item: (-item[0], -item[1], self.movie_map[item[2]]["title"]))
        results = []
        for score, support, movie_id in ranked[:limit]:
            movie = dict(self.movie_map[movie_id])
            movie["score"] = round(score, 4)
            movie["reason"] = "与你相似的用户对这部电影评分较高"
            movie["support"] = round(support, 4)
            results.append(movie)
        return results

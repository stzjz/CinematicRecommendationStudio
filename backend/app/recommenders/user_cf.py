from .base import BaseRecommender, format_score, genre_text


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
        contributors = {}

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
                contributors.setdefault(movie_id, []).append((similarity, other_user, rating))

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
            top_contributors = sorted(contributors.get(movie_id, []), key=lambda item: (-item[0], -item[2]))[:3]
            avg_neighbor_rating = 0.0
            if top_contributors:
                avg_neighbor_rating = sum(item[2] for item in top_contributors) / len(top_contributors)
            movie["score"] = round(score, 4)
            movie["neighbor_count"] = len(contributors.get(movie_id, []))
            movie["reason"] = (
                "协同过滤先找与你评分口味相近的用户；这些相似用户给这部%s片的加权预测分为 %s。"
                % (genre_text(movie), format_score(score))
            )
            movie["reason_details"] = [
                "相似用户加权分 %s" % format_score(score),
                "%s 个邻居贡献" % len(contributors.get(movie_id, [])),
                "邻居均分约 %s" % format_score(avg_neighbor_rating),
            ]
            movie["support"] = round(support, 4)
            results.append(movie)
        return results

    def record_rating(self, user_id, movie_id, rating):
        self.user_ratings.setdefault(user_id, {})[movie_id] = float(rating)

    def delete_rating(self, user_id, movie_id):
        self.user_ratings.get(user_id, {}).pop(movie_id, None)

class CatalogService(object):
    def __init__(self, users, movies, ratings, model_metrics, ablation_results, data_source="memory"):
        self.users = users
        self.movies = movies
        self.ratings = ratings
        self.model_metrics = model_metrics
        self.ablation_results = ablation_results
        self.data_source = data_source
        self.movie_map = dict((movie["movie_id"], movie) for movie in movies)

    def list_users(self):
        return self.users

    def list_hot_movies(self, limit=10):
        aggregates = {}
        for rating in self.ratings:
            movie_id = rating["movie_id"]
            info = aggregates.setdefault(movie_id, {"total": 0.0, "count": 0})
            info["total"] += rating["rating"]
            info["count"] += 1

        ranked = []
        for movie_id, info in aggregates.items():
            score = info["total"] / info["count"]
            ranked.append((score, info["count"], self.movie_map[movie_id]))

        ranked.sort(key=lambda item: (-item[0], -item[1], item[2]["title"]))
        return [item[2] for item in ranked[:limit]]

    def get_movie(self, movie_id):
        return self.movie_map.get(movie_id)

    def get_user_history(self, user_id):
        history = [row for row in self.ratings if row["user_id"] == user_id]
        history.sort(key=lambda row: (-row["rating"], row["movie_id"]))
        results = []
        for row in history:
            movie = self.movie_map.get(row["movie_id"])
            if movie:
                item = dict(movie)
                item["rating"] = row["rating"]
                results.append(item)
        return results

    def get_model_metrics(self):
        return self.model_metrics

    def get_ablation_results(self):
        return self.ablation_results

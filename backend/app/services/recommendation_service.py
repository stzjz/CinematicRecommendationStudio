from app.recommenders.content_based import ContentBasedRecommender
from app.recommenders.lightgcn import LightGCNRecommender
from app.recommenders.popularity import PopularityRecommender
from app.recommenders.user_cf import UserCFRecommender


class RecommendationService(object):
    def __init__(self, movies, ratings, data_source="memory"):
        self.data_source = data_source
        self.recommenders = {
            "popularity": PopularityRecommender(movies, ratings),
            "user_cf": UserCFRecommender(movies, ratings),
            "content_based": ContentBasedRecommender(movies, ratings),
            "lightgcn": LightGCNRecommender(movies, ratings),
        }

    def list_algorithms(self):
        items = []
        for name, recommender in sorted(self.recommenders.items()):
            items.append({"name": name, "description": recommender.description})
        return items

    def recommend(self, user_id, algorithm, limit):
        if algorithm not in self.recommenders:
            raise ValueError("Unsupported algorithm: %s" % algorithm)

        recommender = self.recommenders[algorithm]
        items = recommender.recommend(user_id=user_id, limit=limit)
        meta = {
            "candidate_count": len(items),
            "description": recommender.description,
        }
        if hasattr(recommender, "torch_status"):
            meta["checkpoint_status"] = recommender.torch_status
            meta["checkpoint_error"] = recommender.torch_error
            meta["checkpoint"] = getattr(recommender, "checkpoint_path", "")
            meta["dataset"] = "ml-1m"
            meta["layer"] = 4
            meta["recdim"] = 64
            meta["seed"] = 2026
        return {
            "user_id": user_id,
            "algorithm": algorithm,
            "items": items,
            "meta": meta,
        }

    def record_rating(self, user_id, movie_id, rating):
        for recommender in self.recommenders.values():
            if hasattr(recommender, "record_rating"):
                recommender.record_rating(user_id, movie_id, rating)

    def delete_rating(self, user_id, movie_id):
        for recommender in self.recommenders.values():
            if hasattr(recommender, "delete_rating"):
                recommender.delete_rating(user_id, movie_id)

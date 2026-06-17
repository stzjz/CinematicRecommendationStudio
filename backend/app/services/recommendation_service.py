from app.recommenders.content_based import ContentBasedRecommender
from app.recommenders.lightgcn import LightGCNRecommender
from app.recommenders.ncf import NCFRecommender
from app.recommenders.popularity import PopularityRecommender
from app.recommenders.user_cf import UserCFRecommender


class RecommendationService(object):
    def __init__(self, movies, ratings, movie_tags=None, data_source="memory"):
        self.data_source = data_source
        self.recommenders = {
            "popularity": PopularityRecommender(movies, ratings),
            "user_cf": UserCFRecommender(movies, ratings),
            "content_based": ContentBasedRecommender(movies, ratings, movie_tags or []),
            "lightgcn": LightGCNRecommender(movies, ratings),
            "ncf": NCFRecommender(movies, ratings),
        }

    def list_algorithms(self):
        items = []
        for name, recommender in sorted(self.recommenders.items()):
            items.append({"name": name, "description": recommender.description})
        return items

    def recommend(self, user_id, algorithm, limit, genre_weight=None, tag_weight=None):
        if algorithm not in self.recommenders:
            raise ValueError("Unsupported algorithm: %s" % algorithm)

        recommender = self.recommenders[algorithm]
        if algorithm == "content_based":
            items = recommender.recommend(user_id=user_id, limit=limit, genre_weight=genre_weight, tag_weight=tag_weight)
        else:
            items = recommender.recommend(user_id=user_id, limit=limit)
        meta = {
            "candidate_count": len(items),
            "description": recommender.description,
        }
        if algorithm == "content_based":
            normalized_genre_weight, normalized_tag_weight = recommender._normalized_weights(genre_weight, tag_weight)
            meta["genre_weight"] = round(normalized_genre_weight, 3)
            meta["tag_weight"] = round(normalized_tag_weight, 3)
        if hasattr(recommender, "torch_status"):
            meta["checkpoint_status"] = recommender.torch_status
            meta["checkpoint_error"] = recommender.torch_error
            meta["checkpoint"] = getattr(recommender, "checkpoint_path", "")
        if hasattr(recommender, "metadata"):
            meta.update(recommender.metadata())
        elif algorithm == "lightgcn":
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

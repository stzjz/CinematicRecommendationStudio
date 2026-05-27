from app.recommenders.content_based import ContentBasedRecommender
from app.recommenders.popularity import PopularityRecommender
from app.recommenders.user_cf import UserCFRecommender


class RecommendationService(object):
    def __init__(self, movies, ratings, data_source="memory"):
        self.data_source = data_source
        self.recommenders = {
            "popularity": PopularityRecommender(movies, ratings),
            "user_cf": UserCFRecommender(movies, ratings),
            "content_based": ContentBasedRecommender(movies, ratings),
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
        return {
            "user_id": user_id,
            "algorithm": algorithm,
            "items": items,
            "meta": {
                "candidate_count": len(items),
                "description": recommender.description,
            },
        }

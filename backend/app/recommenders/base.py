class BaseRecommender(object):
    name = "base"
    description = "Base recommender"

    def recommend(self, user_id, limit):
        raise NotImplementedError

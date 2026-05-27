import unittest

from app.sample_data import MOVIES, RATINGS
from app.services.recommendation_service import RecommendationService


class RecommendationServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = RecommendationService(MOVIES, RATINGS)

    def test_supported_algorithms(self):
        names = [item["name"] for item in self.service.list_algorithms()]
        self.assertEqual(sorted(names), ["content_based", "popularity", "user_cf"])

    def test_popularity_recommendation(self):
        result = self.service.recommend(user_id=1, algorithm="popularity", limit=3)
        self.assertEqual(result["algorithm"], "popularity")
        self.assertLessEqual(len(result["items"]), 3)
        for item in result["items"]:
            seen_ids = [1, 2, 4, 7]
            self.assertNotIn(item["movie_id"], seen_ids)

    def test_user_cf_recommendation(self):
        result = self.service.recommend(user_id=1, algorithm="user_cf", limit=5)
        movie_ids = [item["movie_id"] for item in result["items"]]
        self.assertTrue(movie_ids)
        seen_ids = [1, 2, 4, 6, 9, 10, 15, 17, 21, 23]
        for movie_id in movie_ids:
            self.assertNotIn(movie_id, seen_ids)

    def test_content_based_recommendation(self):
        result = self.service.recommend(user_id=3, algorithm="content_based", limit=5)
        self.assertTrue(result["items"])
        for item in result["items"]:
            self.assertIn("reason", item)

    def test_unsupported_algorithm(self):
        with self.assertRaises(ValueError):
            self.service.recommend(user_id=1, algorithm="unknown", limit=5)


if __name__ == "__main__":
    unittest.main()

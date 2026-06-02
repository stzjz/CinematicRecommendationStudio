import unittest

from app.sample_data import MOVIES, RATINGS
from app.sample_data import ABLATION_RESULTS, MODEL_METRICS, USERS
from app.services.catalog_service import CatalogService
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


class CatalogServiceTest(unittest.TestCase):
    def test_movie_detail_contains_rating_summary_and_records(self):
        movie_tags = [
            {"user_id": 1, "movie_id": 1, "tag": "uplifting", "tagged_at": "978300760"},
            {"user_id": 2, "movie_id": 1, "tag": "Uplifting", "tagged_at": "978300761"},
        ]
        service = CatalogService(USERS, MOVIES, RATINGS, movie_tags, MODEL_METRICS, ABLATION_RESULTS)
        detail = service.get_movie_detail(1)

        self.assertEqual(detail["movie_id"], 1)
        self.assertEqual(detail["rating_count"], 2)
        self.assertAlmostEqual(detail["average_rating"], 4.75)
        self.assertTrue(detail["rating_records"])
        self.assertIn("username", detail["rating_records"][0])
        self.assertIn("rated_at", detail["rating_records"][0])
        self.assertNotIn("content", detail["rating_records"][0])
        self.assertEqual(detail["rating_distribution"][0]["rating"], 5)
        self.assertEqual(detail["user_tags"][0]["tag"], "uplifting")
        self.assertEqual(detail["user_tags"][0]["count"], 2)

    def test_hot_boards_use_primary_genre_and_rating_count(self):
        service = CatalogService(USERS, MOVIES, RATINGS, [], MODEL_METRICS, ABLATION_RESULTS)
        boards = service.list_hot_movie_boards(limit_per_genre=3, max_boards=5)
        genres = [board["genre"] for board in boards]

        self.assertIn("Drama", genres)
        drama = [board for board in boards if board["genre"] == "Drama"][0]
        self.assertTrue(drama["items"])
        self.assertIn("rating_count", drama["items"][0])
        counts = [item["rating_count"] for item in drama["items"]]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_user_preference_profile_contains_windowed_taste_without_director_metadata(self):
        movie_tags = [
            {"user_id": 1, "movie_id": 1, "tag": "hopeful", "tagged_at": "978300760"},
            {"user_id": 2, "movie_id": 1, "tag": "prison drama", "tagged_at": "978300761"},
        ]
        service = CatalogService(USERS, MOVIES, RATINGS, movie_tags, MODEL_METRICS, ABLATION_RESULTS)
        profile = service.get_user_preference_profile(1, window="all")

        self.assertEqual(profile["user_id"], 1)
        self.assertEqual(profile["window"]["key"], "all")
        self.assertTrue(profile["genres"])
        self.assertTrue(profile["movie_tags"])
        self.assertFalse(profile["director_status"]["available"])
        self.assertIn("director", profile["director_status"]["reason"])

    def test_create_user_adds_profile_with_next_id(self):
        service = CatalogService(
            [dict(user) for user in USERS],
            MOVIES,
            RATINGS,
            [],
            MODEL_METRICS,
            ABLATION_RESULTS,
        )
        user = service.create_user(username="demo-new-user", age=20, gender="F", occupation="student")

        self.assertEqual(user["user_id"], 4)
        self.assertEqual(user["username"], "demo-new-user")
        self.assertIn(user, service.list_users())

    def test_search_movies_uses_loose_matching(self):
        service = CatalogService(USERS, MOVIES, RATINGS, [], MODEL_METRICS, ABLATION_RESULTS)
        results = service.search_movies("dark crime", limit=5)
        titles = [movie["title"] for movie in results]

        self.assertIn("The Dark Knight", titles)

    def test_rating_crud_updates_user_history(self):
        service = CatalogService(
            [dict(user) for user in USERS],
            MOVIES,
            [dict(row) for row in RATINGS],
            [],
            MODEL_METRICS,
            ABLATION_RESULTS,
        )

        created = service.save_user_rating(1, 3, 4.5, "great crime movie")
        self.assertEqual(created["rating"], 4.5)
        self.assertEqual(created["comment"], "great crime movie")

        updated = service.save_user_rating(1, 3, 3.5, "changed my mind")
        self.assertEqual(updated["rating"], 3.5)
        self.assertEqual(updated["comment"], "changed my mind")

        deleted = service.delete_user_rating(1, 3)
        self.assertTrue(deleted)
        self.assertIsNone(service.get_user_movie_rating(1, 3))


if __name__ == "__main__":
    unittest.main()

USERS = [
    {"user_id": 1, "username": "alice", "age": 22, "gender": "F", "occupation": "student"},
    {"user_id": 2, "username": "bob", "age": 24, "gender": "M", "occupation": "engineer"},
    {"user_id": 3, "username": "carol", "age": 21, "gender": "F", "occupation": "designer"},
]

MOVIES = [
    {"movie_id": 1, "title": "The Shawshank Redemption", "year": 1994, "genres": ["Drama"], "poster_url": "/api/posters/1.svg", "summary": "Hope and friendship survive behind prison walls."},
    {"movie_id": 2, "title": "Inception", "year": 2010, "genres": ["Sci-Fi", "Thriller"], "poster_url": "/api/posters/2.svg", "summary": "A dream thief dives through nested realities."},
    {"movie_id": 3, "title": "The Dark Knight", "year": 2008, "genres": ["Action", "Crime", "Drama"], "poster_url": "/api/posters/3.svg", "summary": "Batman faces chaos unleashed by the Joker."},
    {"movie_id": 4, "title": "La La Land", "year": 2016, "genres": ["Romance", "Drama", "Music"], "poster_url": "/api/posters/4.svg", "summary": "Love and ambition collide under Los Angeles lights."},
    {"movie_id": 5, "title": "Spirited Away", "year": 2001, "genres": ["Animation", "Fantasy", "Adventure"], "poster_url": "/api/posters/5.svg", "summary": "A young girl wanders through a mysterious spirit world."},
    {"movie_id": 6, "title": "Interstellar", "year": 2014, "genres": ["Sci-Fi", "Drama"], "poster_url": "/api/posters/6.svg", "summary": "A desperate space mission searches for humanity's future."},
    {"movie_id": 7, "title": "Your Name", "year": 2016, "genres": ["Animation", "Romance", "Fantasy"], "poster_url": "/api/posters/7.svg", "summary": "Two teenagers connect across time, distance, and memory."},
    {"movie_id": 8, "title": "Coco", "year": 2017, "genres": ["Animation", "Family", "Music"], "poster_url": "/api/posters/8.svg", "summary": "Music and memory guide a boy through the Land of the Dead."},
    {"movie_id": 9, "title": "Parasite", "year": 2019, "genres": ["Thriller", "Drama"], "poster_url": "/api/posters/9.svg", "summary": "A family scheme spirals into a razor-sharp class satire."},
    {"movie_id": 10, "title": "Whiplash", "year": 2014, "genres": ["Drama", "Music"], "poster_url": "/api/posters/10.svg", "summary": "An ambitious drummer is pushed to the brink of greatness."},
    {"movie_id": 11, "title": "The Lord of the Rings: The Fellowship of the Ring", "year": 2001, "genres": ["Fantasy", "Adventure"], "poster_url": "/api/posters/11.svg", "summary": "A fellowship forms to carry a dangerous ring across Middle-earth."},
    {"movie_id": 12, "title": "Spider-Man: Into the Spider-Verse", "year": 2018, "genres": ["Animation", "Action", "Adventure"], "poster_url": "/api/posters/12.svg", "summary": "Miles Morales leaps into a kaleidoscope of spider worlds."},
    {"movie_id": 13, "title": "Dune", "year": 2021, "genres": ["Sci-Fi", "Adventure", "Drama"], "poster_url": "/api/posters/13.svg", "summary": "A young heir confronts destiny on the desert planet Arrakis."},
    {"movie_id": 14, "title": "The Grand Budapest Hotel", "year": 2014, "genres": ["Comedy", "Crime", "Adventure"], "poster_url": "/api/posters/14.svg", "summary": "A concierge and his protege become tangled in a whimsical caper."},
    {"movie_id": 15, "title": "Pride & Prejudice", "year": 2005, "genres": ["Romance", "Drama"], "poster_url": "/api/posters/15.svg", "summary": "Wit, misunderstanding, and love dance through the English countryside."},
    {"movie_id": 16, "title": "Mad Max: Fury Road", "year": 2015, "genres": ["Action", "Sci-Fi", "Adventure"], "poster_url": "/api/posters/16.svg", "summary": "A relentless road war blazes across a post-apocalyptic desert."},
    {"movie_id": 17, "title": "The Truman Show", "year": 1998, "genres": ["Drama", "Sci-Fi"], "poster_url": "/api/posters/17.svg", "summary": "A man slowly discovers that his life is a manufactured spectacle."},
    {"movie_id": 18, "title": "Blade Runner 2049", "year": 2017, "genres": ["Sci-Fi", "Drama", "Mystery"], "poster_url": "/api/posters/18.svg", "summary": "A blade runner uncovers a secret that could reorder society."},
    {"movie_id": 19, "title": "Soul", "year": 2020, "genres": ["Animation", "Family", "Fantasy"], "poster_url": "/api/posters/19.svg", "summary": "A jazz musician searches for meaning between life and the beyond."},
    {"movie_id": 20, "title": "Avengers: Endgame", "year": 2019, "genres": ["Action", "Adventure", "Sci-Fi"], "poster_url": "/api/posters/20.svg", "summary": "Earth's heroes gather for one final stand against Thanos."},
    {"movie_id": 21, "title": "Little Women", "year": 2019, "genres": ["Drama", "Romance"], "poster_url": "/api/posters/21.svg", "summary": "The March sisters grow into themselves through love, loss, and art."},
    {"movie_id": 22, "title": "Everything Everywhere All at Once", "year": 2022, "genres": ["Sci-Fi", "Adventure", "Comedy"], "poster_url": "/api/posters/22.svg", "summary": "An exhausted laundromat owner collides with the multiverse."},
    {"movie_id": 23, "title": "The Social Network", "year": 2010, "genres": ["Drama"], "poster_url": "/api/posters/23.svg", "summary": "Ambition and betrayal race behind the rise of a social platform."},
    {"movie_id": 24, "title": "Howl's Moving Castle", "year": 2004, "genres": ["Animation", "Fantasy", "Romance"], "poster_url": "/api/posters/24.svg", "summary": "A cursed girl steps into a wandering castle and an enchanted war."}
]

RATINGS = [
    {"user_id": 1, "movie_id": 1, "rating": 5.0},
    {"user_id": 1, "movie_id": 2, "rating": 4.5},
    {"user_id": 1, "movie_id": 4, "rating": 4.0},
    {"user_id": 1, "movie_id": 6, "rating": 4.5},
    {"user_id": 1, "movie_id": 9, "rating": 4.5},
    {"user_id": 1, "movie_id": 10, "rating": 4.0},
    {"user_id": 1, "movie_id": 15, "rating": 4.5},
    {"user_id": 1, "movie_id": 17, "rating": 4.5},
    {"user_id": 1, "movie_id": 21, "rating": 4.0},
    {"user_id": 1, "movie_id": 23, "rating": 5.0},

    {"user_id": 2, "movie_id": 1, "rating": 4.5},
    {"user_id": 2, "movie_id": 2, "rating": 5.0},
    {"user_id": 2, "movie_id": 3, "rating": 5.0},
    {"user_id": 2, "movie_id": 6, "rating": 4.5},
    {"user_id": 2, "movie_id": 11, "rating": 4.5},
    {"user_id": 2, "movie_id": 12, "rating": 4.5},
    {"user_id": 2, "movie_id": 13, "rating": 4.0},
    {"user_id": 2, "movie_id": 16, "rating": 5.0},
    {"user_id": 2, "movie_id": 18, "rating": 4.5},
    {"user_id": 2, "movie_id": 20, "rating": 4.5},
    {"user_id": 2, "movie_id": 22, "rating": 4.0},

    {"user_id": 3, "movie_id": 4, "rating": 4.5},
    {"user_id": 3, "movie_id": 5, "rating": 5.0},
    {"user_id": 3, "movie_id": 7, "rating": 5.0},
    {"user_id": 3, "movie_id": 8, "rating": 4.5},
    {"user_id": 3, "movie_id": 11, "rating": 4.0},
    {"user_id": 3, "movie_id": 14, "rating": 4.0},
    {"user_id": 3, "movie_id": 15, "rating": 4.5},
    {"user_id": 3, "movie_id": 19, "rating": 5.0},
    {"user_id": 3, "movie_id": 21, "rating": 4.5},
    {"user_id": 3, "movie_id": 24, "rating": 5.0}
]

MODEL_METRICS = [
    {"model_name": "popularity", "hr10": 0.6200, "ndcg10": 0.3510, "remark": "cold-start fallback baseline"},
    {"model_name": "user_cf", "hr10": 0.6810, "ndcg10": 0.3940, "remark": "classic collaborative filtering baseline"},
    {"model_name": "content_based", "hr10": 0.6550, "ndcg10": 0.3720, "remark": "genre-driven explainable baseline"}
]

ABLATION_RESULTS = [
    {"model_name": "neumf", "embedding_dim": 8, "negative_ratio": 4, "mlp_layers": 2, "hr10": 0.6880, "ndcg10": 0.4010},
    {"model_name": "neumf", "embedding_dim": 16, "negative_ratio": 4, "mlp_layers": 3, "hr10": 0.7010, "ndcg10": 0.4190},
    {"model_name": "neumf", "embedding_dim": 32, "negative_ratio": 4, "mlp_layers": 4, "hr10": 0.7090, "ndcg10": 0.4230}
]

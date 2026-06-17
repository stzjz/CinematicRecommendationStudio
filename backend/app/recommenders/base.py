class BaseRecommender(object):
    name = "base"
    description = "Base recommender"

    def recommend(self, user_id, limit):
        raise NotImplementedError


def top_genres(movie, limit=2):
    genres = movie.get("genres") or []
    return [genre for genre in genres[:limit] if genre]


def genre_text(movie, fallback="类型特征"):
    genres = top_genres(movie, 2)
    return " / ".join(genres) if genres else fallback


def format_score(value, digits=2):
    try:
        return ("%." + str(digits) + "f") % float(value)
    except Exception:
        return "-"

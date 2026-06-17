from .base import BaseRecommender, format_score, genre_text


class ContentBasedRecommender(BaseRecommender):
    name = "content_based"
    description = "Content-based hybrid using movie genres and community free-tag preference"

    def __init__(self, movies, ratings, movie_tags):
        self.movies = movies
        self.ratings = ratings
        self.movie_tags = movie_tags or []
        self.movie_map = dict((movie["movie_id"], movie) for movie in movies)
        self.user_ratings = {}
        self.tags_by_movie = {}
        self._build_indexes()

    def _build_indexes(self):
        for row in self.ratings:
            self.user_ratings.setdefault(row["user_id"], {})[row["movie_id"]] = float(row["rating"])
        for row in self.movie_tags:
            movie_id = row.get("movie_id")
            tag = (row.get("tag") or "").strip()
            if movie_id is None or not tag:
                continue
            self.tags_by_movie.setdefault(movie_id, []).append(row)

    def _normalized_weights(self, genre_weight=None, tag_weight=None):
        try:
            genre_value = float(genre_weight)
        except (TypeError, ValueError):
            genre_value = 0.4
        try:
            tag_value = float(tag_weight)
        except (TypeError, ValueError):
            tag_value = 0.6
        genre_value = max(0.0, genre_value)
        tag_value = max(0.0, tag_value)
        total = genre_value + tag_value
        if total <= 0:
            return 0.4, 0.6
        return genre_value / total, tag_value / total

    def _movie_tag_counts(self, movie_id):
        counts = {}
        labels = {}
        for row in self.tags_by_movie.get(movie_id, []):
            tag = (row.get("tag") or "").strip()
            if not tag:
                continue
            key = tag.lower()
            counts[key] = counts.get(key, 0) + 1
            labels.setdefault(key, tag)
        return counts, labels

    def _build_profiles(self, user_id):
        genre_profile = {}
        tag_profile = {}
        tag_labels = {}
        for movie_id, rating in self.user_ratings.get(user_id, {}).items():
            if rating < 4.0:
                continue
            movie = self.movie_map.get(movie_id)
            if not movie:
                continue
            for genre in movie.get("genres") or []:
                genre_profile[genre] = genre_profile.get(genre, 0.0) + rating

            tag_counts, labels = self._movie_tag_counts(movie_id)
            for key, count in tag_counts.items():
                tag_profile[key] = tag_profile.get(key, 0.0) + rating * count
                tag_labels.setdefault(key, labels.get(key, key))
        return genre_profile, tag_profile, tag_labels

    def _favorite_examples(self, user_id, matched_genres, matched_tags):
        examples = []
        matched_genre_set = set(matched_genres)
        matched_tag_set = set(key for key, _label, _score in matched_tags)
        for movie_id, rating in sorted(self.user_ratings.get(user_id, {}).items(), key=lambda item: -item[1]):
            if rating < 4.0:
                continue
            movie = self.movie_map.get(movie_id)
            if not movie:
                continue
            tag_counts, _labels = self._movie_tag_counts(movie_id)
            if (set(movie.get("genres") or []) & matched_genre_set) or (set(tag_counts) & matched_tag_set):
                examples.append(movie["title"])
            if len(examples) >= 2:
                break
        return examples

    def recommend(self, user_id, limit, genre_weight=None, tag_weight=None):
        seen = set(self.user_ratings.get(user_id, {}))
        genre_profile, tag_profile, tag_labels = self._build_profiles(user_id)
        genre_weight, tag_weight = self._normalized_weights(genre_weight, tag_weight)
        ranked = []

        for movie in self.movies:
            movie_id = movie["movie_id"]
            if movie_id in seen:
                continue

            genre_score = 0.0
            matched_genres = []
            for genre in movie.get("genres") or []:
                value = genre_profile.get(genre, 0.0)
                if value > 0:
                    genre_score += value
                    matched_genres.append(genre)

            tag_score = 0.0
            matched_tags = []
            tag_counts, labels = self._movie_tag_counts(movie_id)
            for key, count in tag_counts.items():
                value = tag_profile.get(key, 0.0)
                if value > 0:
                    contribution = value * count
                    tag_score += contribution
                    matched_tags.append((key, labels.get(key) or tag_labels.get(key) or key, contribution))

            score = genre_weight * genre_score + tag_weight * tag_score
            if score <= 0:
                continue
            matched_tags.sort(key=lambda item: (-item[2], item[1].lower()))
            ranked.append((score, genre_score, tag_score, matched_genres, matched_tags, movie_id))

        ranked.sort(key=lambda item: (-item[0], self.movie_map[item[5]]["title"]))
        results = []
        for score, genre_score, tag_score, matched_genres, matched_tags, movie_id in ranked[:limit]:
            movie = dict(self.movie_map[movie_id])
            genre_copy = " / ".join(matched_genres[:3]) if matched_genres else genre_text(movie)
            tag_copy = " / ".join(tag for _key, tag, _value in matched_tags[:4])
            examples = self._favorite_examples(user_id, matched_genres, matched_tags[:4])
            movie["score"] = round(score, 4)
            movie["genre_score"] = round(genre_score, 4)
            movie["tag_score"] = round(tag_score, 4)
            movie["genre_weight"] = round(genre_weight, 3)
            movie["tag_weight"] = round(tag_weight, 3)
            movie["matched_genres"] = matched_genres[:4]
            movie["matched_tags"] = [tag for _key, tag, _value in matched_tags[:6]]
            if tag_copy:
                movie["reason"] = (
                    "混合内容推荐同时看主类型和自由标签；这部电影命中 %s，并匹配自由标签 %s。"
                    % (genre_copy, tag_copy)
                )
            else:
                movie["reason"] = (
                    "混合内容推荐同时看主类型和自由标签；这部电影主要命中 %s，暂无可用自由标签命中。"
                    % genre_copy
                )
            movie["reason_details"] = [
                "主类型权重 %s · 自由标签权重 %s" % (format_score(genre_weight), format_score(tag_weight)),
                "命中类型：%s" % genre_copy,
                "综合得分 %s" % format_score(score),
            ]
            if tag_copy:
                movie["reason_details"].insert(2, "命中自由标签：%s" % tag_copy)
            if examples:
                movie["reason_details"].append("参考历史：%s" % "、".join(examples))
            results.append(movie)
        return results

    def metadata(self):
        return {
            "default_genre_weight": 0.4,
            "default_tag_weight": 0.6,
            "tag_movie_count": len(self.tags_by_movie),
        }

    def record_rating(self, user_id, movie_id, rating):
        self.user_ratings.setdefault(user_id, {})[movie_id] = float(rating)

    def delete_rating(self, user_id, movie_id):
        self.user_ratings.get(user_id, {}).pop(movie_id, None)

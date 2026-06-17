import os
import sys

from .base import BaseRecommender, format_score, genre_text


class NCFRecommender(BaseRecommender):
    name = "ncf"
    description = "NeuMF checkpoint from the local NCF project, with popularity fallback when torch is unavailable"

    def __init__(self, movies, ratings, project_root=None):
        self.movies = movies
        self.ratings = ratings
        self.movie_map = dict((movie["movie_id"], movie) for movie in movies)
        self.project_root = project_root or self._default_project_root()
        self.ncf_root = os.path.join(os.path.dirname(self.project_root), "BigDataHomework", "lizhixiang", "NCF")
        self.dataset_path = os.path.join(self.ncf_root, "datasets", "ml-1m")
        self.checkpoint_path = os.path.join(self.ncf_root, "models", "ml-1m", "NeuMF-end.pth")
        self.user_seen = {}
        self.ncf_train_items = {}
        self.item_to_movie_id = {}
        self.movie_id_to_item = {}
        self.torch_status = "not_checked"
        self.torch_error = ""
        self.model_name = "NeuMF-end"
        self.factor_num = 32
        self.num_layers = 3
        self.user_num = 0
        self.item_num = 0
        self._model = None
        self._torch = None
        self._build_indexes()
        self._try_load_checkpoint()

    def _default_project_root(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

    def _build_indexes(self):
        for rating in self.ratings:
            self.user_seen.setdefault(int(rating["user_id"]), set()).add(int(rating["movie_id"]))

        ordered_movies = sorted(self.movies, key=lambda movie: movie["movie_id"])
        for item_index, movie in enumerate(ordered_movies[:3706]):
            self.item_to_movie_id[item_index] = movie["movie_id"]
            self.movie_id_to_item[movie["movie_id"]] = item_index

        train_file = os.path.join(self.dataset_path, "ml-1m.train.rating")
        if not os.path.exists(train_file):
            return
        with open(train_file) as handle:
            for line in handle:
                parts = line.strip().split("\t")
                if len(parts) < 2:
                    continue
                user = int(parts[0])
                item = int(parts[1])
                self.ncf_train_items.setdefault(user, set()).add(item)

    def _try_load_checkpoint(self):
        try:
            import torch
        except Exception as exc:
            self.torch_status = "fallback"
            self.torch_error = "torch unavailable: %s" % exc
            return
        if not os.path.exists(self.checkpoint_path):
            self.torch_status = "fallback"
            self.torch_error = "checkpoint not found: %s" % self.checkpoint_path
            return
        try:
            if self.ncf_root not in sys.path:
                sys.path.insert(0, self.ncf_root)
            try:
                model = torch.load(self.checkpoint_path, map_location="cpu", weights_only=False)
            except TypeError:
                model = torch.load(self.checkpoint_path, map_location="cpu")
            model.eval()
            self._model = model
            self._torch = torch
            self.model_name = getattr(model, "model", self.model_name)
            self.user_num = int(model.embed_user_GMF.weight.shape[0])
            self.item_num = int(model.embed_item_GMF.weight.shape[0])
            self.factor_num = int(model.embed_user_GMF.weight.shape[1])
            mlp_width = int(model.embed_user_MLP.weight.shape[1])
            self.num_layers = 1
            while self.factor_num * (2 ** (self.num_layers - 1)) < mlp_width:
                self.num_layers += 1
            self.torch_status = "checkpoint"
            self.torch_error = ""
        except Exception as exc:
            self.torch_status = "fallback"
            self.torch_error = "checkpoint load failed: %s" % exc

    def _ncf_user_id(self, user_id):
        user_id = int(user_id)
        if user_id in self.ncf_train_items:
            return user_id
        if user_id - 1 in self.ncf_train_items:
            return user_id - 1
        if self.user_num:
            return user_id % self.user_num
        if self.ncf_train_items:
            return user_id % len(self.ncf_train_items)
        return user_id

    def _checkpoint_recommend(self, user_id, limit):
        if self.torch_status != "checkpoint" or self._model is None or self._torch is None:
            return []
        ncf_user = self._ncf_user_id(user_id)
        if ncf_user < 0 or ncf_user >= self.user_num:
            return []
        seen_movie_ids = self.user_seen.get(int(user_id), set())
        seen_items = self.ncf_train_items.get(ncf_user, set())
        candidate_items = [
            item
            for item in range(min(self.item_num, len(self.item_to_movie_id)))
            if item not in seen_items
            and self.item_to_movie_id.get(item) not in seen_movie_ids
            and self.item_to_movie_id.get(item) in self.movie_map
        ]
        if not candidate_items:
            return []
        scores = self._score_items(ncf_user, candidate_items)
        ranked = sorted(zip(scores, candidate_items), key=lambda row: (-row[0], row[1]))[:limit]
        return self._format_results(ranked, ncf_user)

    def _score_items(self, ncf_user, candidate_items, batch_size=512):
        torch = self._torch
        scores = []
        with torch.no_grad():
            for start in range(0, len(candidate_items), batch_size):
                batch_items = candidate_items[start : start + batch_size]
                users = torch.full((len(batch_items),), ncf_user, dtype=torch.long)
                items = torch.tensor(batch_items, dtype=torch.long)
                batch_scores = self._model(users, items).detach().cpu().tolist()
                scores.extend(float(score) for score in batch_scores)
        return scores

    def _format_results(self, ranked, ncf_user):
        results = []
        for rank, (score, item_index) in enumerate(ranked, start=1):
            movie_id = self.item_to_movie_id.get(item_index)
            if not movie_id or movie_id not in self.movie_map:
                continue
            movie = dict(self.movie_map[movie_id])
            signals = self._explain_pair(ncf_user, item_index)
            movie["score"] = round(float(score), 6)
            movie["support"] = 0
            movie["ncf_item_index"] = item_index
            movie["ncf_user_index"] = ncf_user
            movie["ncf_rank"] = rank
            movie["ncf_model"] = self.model_name
            movie["ncf_gmf_signal"] = signals["gmf"]
            movie["ncf_mlp_signal"] = signals["mlp"]
            movie["reason"] = (
                "NCF/NeuMF 同时看线性协同信号和非线性偏好匹配；这部%s片的融合得分为 %s。"
                % (genre_text(movie), format_score(score, 3))
            )
            movie["reason_details"] = [
                "融合得分 %s" % format_score(score, 3),
                "GMF 信号 %s" % format_score(signals["gmf"], 3),
                "MLP 相似 %s" % format_score(signals["mlp"], 3),
            ]
            results.append(movie)
        return results

    def _explain_pair(self, ncf_user, item_index):
        if self._model is None or self._torch is None:
            return {"gmf": 0.0, "mlp": 0.0}
        torch = self._torch
        with torch.no_grad():
            user = torch.tensor([ncf_user], dtype=torch.long)
            item = torch.tensor([item_index], dtype=torch.long)
            user_gmf = self._model.embed_user_GMF(user)
            item_gmf = self._model.embed_item_GMF(item)
            gmf_signal = (user_gmf * item_gmf).sum().item()
            user_mlp = self._model.embed_user_MLP(user)
            item_mlp = self._model.embed_item_MLP(item)
            mlp_signal = torch.nn.functional.cosine_similarity(user_mlp, item_mlp).item()
        return {"gmf": round(float(gmf_signal), 6), "mlp": round(float(mlp_signal), 6)}

    def _fallback_recommend(self, user_id, limit):
        seen_movie_ids = self.user_seen.get(int(user_id), set())
        counts = {}
        totals = {}
        for rating in self.ratings:
            movie_id = int(rating["movie_id"])
            if movie_id in seen_movie_ids or movie_id not in self.movie_map:
                continue
            counts[movie_id] = counts.get(movie_id, 0) + 1
            totals[movie_id] = totals.get(movie_id, 0.0) + float(rating["rating"])
        ranked = sorted(
            counts,
            key=lambda movie_id: (-counts[movie_id], -(totals[movie_id] / max(counts[movie_id], 1)), movie_id),
        )[:limit]
        results = []
        for rank, movie_id in enumerate(ranked, start=1):
            movie = dict(self.movie_map[movie_id])
            movie["score"] = round(totals[movie_id] / max(counts[movie_id], 1), 6)
            movie["support"] = counts[movie_id]
            movie["ncf_rank"] = rank
            movie["ncf_source"] = "fallback"
            movie["reason"] = (
                "NCF checkpoint 不可用时退回热门评分兜底；这部%s片均分 %s，评分数 %s。"
                % (genre_text(movie), format_score(movie["score"]), counts[movie_id])
            )
            movie["reason_details"] = [
                "兜底排序",
                "均分 %s" % format_score(movie["score"]),
                "%s 条评分" % counts[movie_id],
            ]
            results.append(movie)
        return results

    def metadata(self):
        return {
            "checkpoint_status": self.torch_status,
            "checkpoint_error": self.torch_error,
            "checkpoint": self.checkpoint_path,
            "dataset": "ml-1m",
            "model": self.model_name,
            "factor_num": self.factor_num,
            "num_layers": self.num_layers,
            "user_num": self.user_num,
            "item_num": self.item_num,
        }

    def recommend(self, user_id, limit):
        items = self._checkpoint_recommend(user_id, limit)
        if items:
            return items
        return self._fallback_recommend(user_id, limit)

    def record_rating(self, user_id, movie_id, rating):
        self.user_seen.setdefault(int(user_id), set()).add(int(movie_id))

    def delete_rating(self, user_id, movie_id):
        self.user_seen.get(int(user_id), set()).discard(int(movie_id))

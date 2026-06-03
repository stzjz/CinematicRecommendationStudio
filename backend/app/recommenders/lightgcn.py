import math
import os
import warnings

from .base import BaseRecommender


class LightGCNRecommender(BaseRecommender):
    name = "lightgcn"
    description = "LightGCN checkpoint on MovieLens-1M graph, with graph-neighborhood fallback when torch is unavailable"

    def __init__(self, movies, ratings, project_root=None):
        self.movies = movies
        self.ratings = ratings
        self.movie_map = dict((movie["movie_id"], movie) for movie in movies)
        self.project_root = project_root or self._default_project_root()
        self.lightgcn_root = os.path.join(os.path.dirname(self.project_root), "BigDataHomework", "LightGCN")
        self.dataset_path = os.path.join(self.lightgcn_root, "data", "ml-1m")
        self.checkpoint_path = os.path.join(self.lightgcn_root, "code", "checkpoints", "lgn-ml-1m-4-64.pth.tar")
        self.user_train_items = {}
        self.item_users = {}
        self.user_seen = {}
        self.item_to_movie_id = {}
        self.movie_id_to_item = {}
        self.torch_status = "not_checked"
        self.torch_error = ""
        self._torch_scores = None
        self._build_indexes()
        self._try_load_checkpoint_scores()

    def _default_project_root(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

    def _build_indexes(self):
        for rating in self.ratings:
            self.user_seen.setdefault(int(rating["user_id"]), set()).add(int(rating["movie_id"]))

        ordered_movies = sorted(self.movies, key=lambda movie: movie["movie_id"])
        for item_index, movie in enumerate(ordered_movies[:3706]):
            self.item_to_movie_id[item_index] = movie["movie_id"]
            self.movie_id_to_item[movie["movie_id"]] = item_index

        train_file = os.path.join(self.dataset_path, "train.txt")
        if not os.path.exists(train_file):
            return
        with open(train_file) as handle:
            for line in handle:
                parts = [int(value) for value in line.strip().split() if value]
                if not parts:
                    continue
                user = parts[0]
                items = parts[1:]
                self.user_train_items[user] = set(items)
                for item in items:
                    self.item_users.setdefault(item, set()).add(user)

    def _try_load_checkpoint_scores(self):
        try:
            import torch
            import numpy as np
        except Exception as exc:
            self.torch_status = "fallback"
            self.torch_error = "torch unavailable: %s" % exc
            return
        if not os.path.exists(self.checkpoint_path):
            self.torch_status = "fallback"
            self.torch_error = "checkpoint not found: %s" % self.checkpoint_path
            return
        try:
            state = torch.load(self.checkpoint_path, map_location="cpu")
            user_key = "embedding_user.weight"
            item_key = "embedding_item.weight"
            if user_key not in state or item_key not in state:
                self.torch_status = "fallback"
                self.torch_error = "checkpoint does not expose raw embedding weights"
                return
            graph_path = os.path.join(self.dataset_path, "s_pre_adj_mat.npz")
            user_ego = state[user_key].float()
            item_ego = state[item_key].float()
            if os.path.exists(graph_path):
                graph_data = np.load(graph_path)
                indptr = graph_data["indptr"]
                indices = graph_data["indices"]
                values = graph_data["data"]
                shape = tuple(int(value) for value in graph_data["shape"])
                rows = np.repeat(np.arange(shape[0]), np.diff(indptr))
                sparse_index = torch.from_numpy(np.vstack([rows, indices]).astype(np.int64))
                sparse_value = torch.tensor(values, dtype=torch.float32)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    graph = torch.sparse_coo_tensor(sparse_index, sparse_value, torch.Size(shape), check_invariants=False).coalesce()
                all_emb = torch.cat([user_ego, item_ego], dim=0)
                layers = [all_emb]
                with torch.no_grad():
                    for _ in range(4):
                        all_emb = torch.sparse.mm(graph, all_emb)
                        layers.append(all_emb)
                    light_out = torch.stack(layers, dim=1).mean(dim=1)
                self._user_embeddings = light_out[: user_ego.shape[0]]
                self._item_embeddings = light_out[user_ego.shape[0] :]
            else:
                self._user_embeddings = user_ego
                self._item_embeddings = item_ego
            self.torch_status = "checkpoint"
            self.torch_error = ""
        except Exception as exc:
            self.torch_status = "fallback"
            self.torch_error = "checkpoint load failed: %s" % exc

    def _lightgcn_user_id(self, user_id):
        user_id = int(user_id)
        if user_id in self.user_train_items:
            return user_id
        if user_id - 1 in self.user_train_items:
            return user_id - 1
        if self.user_train_items:
            return user_id % len(self.user_train_items)
        return user_id

    def _checkpoint_recommend(self, user_id, limit):
        try:
            import torch
        except Exception:
            return []
        if self.torch_status != "checkpoint":
            return []
        lgn_user = self._lightgcn_user_id(user_id)
        if lgn_user >= self._user_embeddings.shape[0]:
            return []
        user_emb = self._user_embeddings[lgn_user]
        scores = torch.matmul(self._item_embeddings, user_emb)
        seen_movie_ids = self.user_seen.get(int(user_id), set())
        seen_items = self.user_train_items.get(lgn_user, set())
        ranked = []
        for item_index, score in enumerate(scores.tolist()):
            movie_id = self.item_to_movie_id.get(item_index)
            if not movie_id or movie_id in seen_movie_ids or item_index in seen_items:
                continue
            if movie_id not in self.movie_map:
                continue
            ranked.append((float(score), item_index, movie_id))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return self._format_results(ranked[:limit], source="checkpoint", lgn_user=lgn_user)

    def _fallback_recommend(self, user_id, limit):
        lgn_user = self._lightgcn_user_id(user_id)
        seed_items = sorted(
            self.user_train_items.get(lgn_user, set()),
            key=lambda item: (len(self.item_users.get(item, [])), item),
        )[:32]
        seen_movie_ids = self.user_seen.get(int(user_id), set())
        scores = {}
        supports = {}
        for seed_item in seed_items:
            neighbors = sorted(self.item_users.get(seed_item, set()))[:160]
            seed_degree = max(len(neighbors), 1)
            for neighbor in neighbors:
                for candidate in list(self.user_train_items.get(neighbor, set()))[:160]:
                    if candidate in seed_items:
                        continue
                    movie_id = self.item_to_movie_id.get(candidate)
                    if not movie_id or movie_id in seen_movie_ids or movie_id not in self.movie_map:
                        continue
                    weight = 1.0 / math.sqrt(seed_degree * max(len(self.item_users.get(candidate, [])), 1))
                    scores[candidate] = scores.get(candidate, 0.0) + weight
                    supports[candidate] = supports.get(candidate, 0) + 1
                    if len(scores) >= 2500:
                        break
                if len(scores) >= 2500:
                    break
            if len(scores) >= 2500:
                break
        ranked = [(score, item, self.item_to_movie_id[item]) for item, score in scores.items()]
        ranked.sort(key=lambda item: (-item[0], -supports.get(item[1], 0), item[1]))
        return self._format_results(ranked[:limit], source="graph_fallback", lgn_user=lgn_user, supports=supports)

    def _format_results(self, ranked, source, lgn_user, supports=None):
        supports = supports or {}
        results = []
        for rank, (score, item_index, movie_id) in enumerate(ranked, start=1):
            movie = dict(self.movie_map[movie_id])
            movie["score"] = round(float(score), 6)
            movie["support"] = int(supports.get(item_index, len(self.item_users.get(item_index, []))))
            movie["lightgcn_item_index"] = item_index
            movie["lightgcn_user_index"] = lgn_user
            movie["lightgcn_rank"] = rank
            movie["lightgcn_source"] = source
            movie["reason"] = "LightGCN 在用户-电影交互图上传播偏好后给出的高分候选"
            results.append(movie)
        return results

    def recommend(self, user_id, limit):
        items = self._checkpoint_recommend(user_id, limit)
        if items:
            return items
        return self._fallback_recommend(user_id, limit)

    def record_rating(self, user_id, movie_id, rating):
        self.user_seen.setdefault(int(user_id), set()).add(int(movie_id))

    def delete_rating(self, user_id, movie_id):
        self.user_seen.get(int(user_id), set()).discard(int(movie_id))

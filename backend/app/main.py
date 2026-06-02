from __future__ import print_function

import json

from app.bootstrap import build_services
from app.posters import build_poster_svg

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, Response
    from pydantic import BaseModel
except ImportError:
    FastAPI = None
    HTTPException = Exception
    Query = None
    CORSMiddleware = None
    HTMLResponse = None
    BaseModel = object


class UserCreatePayload(BaseModel):
    username: str
    age: int | None = None
    gender: str | None = None
    occupation: str | None = None


class RatingPayload(BaseModel):
    movie_id: int
    rating: float
    comment: str | None = None


def render_homepage():
    payload = {
        "title": "CineMatch Demo",
        "subtitle": "Movie Recommendation Showcase",
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CineMatch Demo</title>
  <style>
    :root {
      --bg: #09111f;
      --panel: rgba(10, 19, 37, 0.86);
      --panel-soft: rgba(19, 31, 56, 0.74);
      --line: rgba(255, 255, 255, 0.08);
      --text: #f6f4ee;
      --muted: #a9b4c9;
      --gold: #ffbf47;
      --rose: #ff6b6b;
      --cyan: #58d7ff;
      --shadow: 0 20px 80px rgba(0, 0, 0, 0.35);
      --radius: 24px;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(255, 191, 71, 0.2), transparent 28%),
        radial-gradient(circle at top right, rgba(88, 215, 255, 0.15), transparent 24%),
        linear-gradient(180deg, #13213e 0%, #09111f 45%, #050a12 100%);
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      min-height: 100vh;
    }

    .shell {
      width: min(1180px, calc(100vw - 32px));
      margin: 20px auto 40px;
    }

    .hero {
      position: relative;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 30px;
      padding: 40px;
      background:
        linear-gradient(135deg, rgba(255, 191, 71, 0.16), rgba(255, 107, 107, 0.08)),
        linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02));
      box-shadow: var(--shadow);
    }

    .hero::after {
      content: "";
      position: absolute;
      inset: auto -80px -80px auto;
      width: 260px;
      height: 260px;
      background: radial-gradient(circle, rgba(88, 215, 255, 0.3), transparent 68%);
      pointer-events: none;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--gold);
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    h1 {
      margin: 16px 0 10px;
      font-size: clamp(34px, 6vw, 66px);
      line-height: 0.95;
      max-width: 720px;
    }

    .hero p {
      margin: 0;
      max-width: 640px;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.7;
    }

    .hero-grid {
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 18px;
      margin-top: 28px;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--panel);
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
    }

    .controls { padding: 22px; }

    .control-row {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }

    label {
      display: block;
      margin-bottom: 8px;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    select, button {
      width: 100%;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.05);
      color: var(--text);
      padding: 14px 16px;
      font-size: 15px;
    }

    option { color: #101520; }

    button {
      margin-top: 20px;
      cursor: pointer;
      background: linear-gradient(135deg, var(--gold), #ff8f5a);
      color: #1b1406;
      font-weight: 700;
      border: 0;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      box-shadow: 0 10px 30px rgba(255, 191, 71, 0.25);
    }

    button:hover { transform: translateY(-1px); }

    .hero-stats {
      display: grid;
      gap: 14px;
      padding: 22px;
      background: var(--panel-soft);
    }

    .stat-card {
      border-radius: 18px;
      padding: 18px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stat-card strong {
      display: block;
      font-size: 28px;
      margin-bottom: 6px;
    }

    .stat-card span {
      color: var(--muted);
      font-size: 13px;
    }

    .content {
      display: grid;
      grid-template-columns: 1.35fr 0.95fr;
      gap: 18px;
      margin-top: 18px;
    }

    .section { padding: 22px; }

    .section-head {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
    }

    .section-head h2 {
      margin: 0;
      font-size: 22px;
    }

    .section-head p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }

    .movie-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 14px;
    }

    .movie-card {
      position: relative;
      overflow: hidden;
      min-height: 220px;
      border-radius: 20px;
      padding: 18px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.02)),
        linear-gradient(135deg, rgba(88, 215, 255, 0.12), rgba(255, 107, 107, 0.05));
      border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .movie-badge {
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(0, 0, 0, 0.24);
      color: var(--gold);
      font-size: 12px;
      margin-bottom: 12px;
    }

    .movie-card h3 {
      margin: 0 0 10px;
      font-size: 24px;
      line-height: 1.05;
    }

    .movie-meta, .movie-reason {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }

    .movie-reason { margin-top: 12px; }

    .mini-list {
      display: grid;
      gap: 12px;
    }

    .mini-item {
      padding: 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .mini-item h3, .mini-item h4 { margin: 0 0 6px; }

    .mini-item p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }

    .score {
      display: inline-block;
      margin-top: 10px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255, 191, 71, 0.12);
      color: var(--gold);
      font-size: 12px;
      font-weight: 700;
    }

    .footer-note {
      margin-top: 18px;
      text-align: center;
      color: var(--muted);
      font-size: 13px;
    }

    .footer-note a { color: var(--cyan); }

    .loading {
      color: var(--muted);
      padding: 10px 2px;
    }

    @media (max-width: 920px) {
      .hero-grid, .content, .control-row {
        grid-template-columns: 1fr;
      }
      .hero { padding: 28px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="eyebrow">Recommendation System Demo</div>
      <h1 id="hero-title">CineMatch Demo</h1>
      <p id="hero-subtitle">把推荐算法接口和课程答辩展示放在同一个可访问首页里，打开根路径就能直接看到系统状态、热门电影和个性推荐。</p>
      <div class="hero-grid">
        <div class="panel controls">
          <div class="control-row">
            <div>
              <label for="user-select">User</label>
              <select id="user-select"></select>
            </div>
            <div>
              <label for="algorithm-select">Algorithm</label>
              <select id="algorithm-select"></select>
            </div>
            <div>
              <label for="limit-select">Top N</label>
              <select id="limit-select">
                <option value="4">Top 4</option>
                <option value="6" selected>Top 6</option>
                <option value="8">Top 8</option>
              </select>
            </div>
          </div>
          <button id="refresh-btn">刷新推荐结果</button>
        </div>
        <div class="panel hero-stats" id="hero-stats">
          <div class="stat-card"><strong id="data-source">-</strong><span>当前数据源</span></div>
          <div class="stat-card"><strong id="user-count">-</strong><span>可用用户数</span></div>
          <div class="stat-card"><strong id="algo-count">-</strong><span>推荐算法数</span></div>
        </div>
      </div>
    </section>

    <section class="content">
      <div class="panel section">
        <div class="section-head">
          <div>
            <h2>个性推荐</h2>
            <p id="recommendation-desc">等待加载推荐结果</p>
          </div>
        </div>
        <div id="recommendations" class="movie-grid">
          <div class="loading">正在加载推荐结果...</div>
        </div>
      </div>

    </section>

    <section class="content">
      <div class="panel section">
        <div class="section-head">
          <div>
            <h2>热门电影</h2>
            <p>适合首页展示和冷启动兜底</p>
          </div>
        </div>
        <div id="hot-movies" class="movie-grid">
          <div class="loading">正在加载热门电影...</div>
        </div>
      </div>

      <div class="panel section">
        <div class="section-head">
          <div>
            <h2>用户历史</h2>
            <p>用于解释个性化偏好来源</p>
          </div>
        </div>
        <div id="history" class="mini-list">
          <div class="loading">正在加载用户历史...</div>
        </div>
      </div>
    </section>

    <div class="footer-note">
      API 文档仍然可用：<a href="/docs">/docs</a>
    </div>
  </div>

  <script>
    const pageConfig = __PAGE_CONFIG__;
    const state = {
      users: [],
      algorithms: []
    };

    async function getJson(url) {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Request failed: " + url);
      }
      return response.json();
    }

    function genresText(genres) {
      return (genres || []).join(" / ");
    }

    function renderMovieCards(containerId, items, emptyText) {
      const container = document.getElementById(containerId);
      if (!items.length) {
        container.innerHTML = '<div class="loading">' + emptyText + '</div>';
        return;
      }
      container.innerHTML = items.map(function(item) {
        return `
          <article class="movie-card">
            <div class="movie-badge">${item.year || "Movie"}</div>
            <h3>${item.title}</h3>
            <div class="movie-meta">${genresText(item.genres)}</div>
            <div class="movie-reason">${item.reason || item.summary || "暂无额外说明"}</div>
            ${item.score !== undefined ? `<div class="score">Score ${Number(item.score).toFixed(2)}</div>` : ""}
          </article>
        `;
      }).join("");
    }

    function renderMiniList(containerId, items, renderer, emptyText) {
      const container = document.getElementById(containerId);
      if (!items.length) {
        container.innerHTML = '<div class="loading">' + emptyText + '</div>';
        return;
      }
      container.innerHTML = items.map(renderer).join("");
    }

    function fillSelect(selectId, items, getValue, getLabel) {
      const select = document.getElementById(selectId);
      select.innerHTML = items.map(function(item) {
        return `<option value="${getValue(item)}">${getLabel(item)}</option>`;
      }).join("");
    }

    async function bootstrap() {
      document.getElementById("hero-title").textContent = pageConfig.title;
      document.getElementById("hero-subtitle").textContent = "后端首页现在直接展示推荐系统内容，适合先联调再做正式前端。";

      const [health, users, algorithms, hotMovies] = await Promise.all([
        getJson("/api/health"),
        getJson("/api/users"),
        getJson("/api/algorithms"),
        getJson("/api/movies/hot?limit=4")
      ]);

      state.users = users.items || [];
      state.algorithms = algorithms.items || [];

      fillSelect("user-select", state.users, function(item) { return item.user_id; }, function(item) {
        return item.user_id + " - " + item.username;
      });
      fillSelect("algorithm-select", state.algorithms, function(item) { return item.name; }, function(item) {
        return item.name + " - " + item.description;
      });

      document.getElementById("data-source").textContent = (health.data_source || "-").toUpperCase();
      document.getElementById("user-count").textContent = String(state.users.length);
      document.getElementById("algo-count").textContent = String(state.algorithms.length);

      renderMovieCards("hot-movies", hotMovies.items || [], "暂无热门电影数据");

      await refreshRecommendation();
      document.getElementById("refresh-btn").addEventListener("click", refreshRecommendation);
      document.getElementById("user-select").addEventListener("change", refreshRecommendation);
      document.getElementById("algorithm-select").addEventListener("change", refreshRecommendation);
      document.getElementById("limit-select").addEventListener("change", refreshRecommendation);
    }

    async function refreshRecommendation() {
      const userId = document.getElementById("user-select").value;
      const algorithm = document.getElementById("algorithm-select").value;
      const limit = document.getElementById("limit-select").value;

      const [recommendations, history] = await Promise.all([
        getJson(`/api/recommendations/${userId}?algorithm=${algorithm}&limit=${limit}`),
        getJson(`/api/users/${userId}/history`)
      ]);

      document.getElementById("recommendation-desc").textContent =
        (recommendations.meta && recommendations.meta.description) || "推荐结果";

      renderMovieCards("recommendations", recommendations.items || [], "该用户当前没有可展示的推荐结果");
      renderMiniList("history", history.items || [], function(item) {
        return `
          <article class="mini-item">
            <h4>${item.title}</h4>
            <p>${genresText(item.genres)}</p>
            <div class="score">Rated ${Number(item.rating).toFixed(1)}</div>
          </article>
        `;
      }, "该用户暂无历史记录");
    }

    bootstrap().catch(function(error) {
      const message = error && error.message ? error.message : String(error);
      document.getElementById("recommendations").innerHTML = '<div class="loading">页面加载失败：' + message + '</div>';
    });
  </script>
</body>
</html>
"""
    return html.replace("__PAGE_CONFIG__", payload_json)


def build_app():
    if FastAPI is None:
        raise RuntimeError(
            "FastAPI is not installed. Activate the project environment and run `pip install -r backend/requirements.txt`."
        )

    services = build_services()
    catalog_service = services["catalog_service"]
    recommendation_service = services["recommendation_service"]
    settings = services["settings"]

    app = FastAPI(title="BigDataHomework Recommendation API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    def homepage():
        return render_homepage()

    @app.get("/api/posters/{movie_id}.svg")
    def poster_svg(movie_id: int):
        movie = catalog_service.get_movie(movie_id)
        if movie is None:
            raise HTTPException(status_code=404, detail="Movie not found")
        return Response(content=build_poster_svg(movie), media_type="image/svg+xml")

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "data_source": catalog_service.data_source,
            "db_path": settings["db_path"],
        }

    @app.get("/api/users")
    def list_users(limit: int = Query(200, ge=1, le=1000)):
        return {"items": catalog_service.list_users(limit=limit)}

    @app.post("/api/users")
    def create_user(payload: UserCreatePayload):
        try:
            return catalog_service.create_user(
                username=payload.username,
                age=payload.age,
                gender=payload.gender,
                occupation=payload.occupation,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/algorithms")
    def list_algorithms():
        return {"items": recommendation_service.list_algorithms()}

    @app.get("/api/movies/hot")
    def hot_movies(limit: int = Query(10, ge=1, le=50)):
        return {"items": catalog_service.list_hot_movies(limit=limit)}

    @app.get("/api/movies/hot/boards")
    def hot_movie_boards(
        limit_per_genre: int = Query(5, ge=1, le=20),
        max_boards: int = Query(6, ge=1, le=20),
    ):
        return {"items": catalog_service.list_hot_movie_boards(limit_per_genre=limit_per_genre, max_boards=max_boards)}

    @app.get("/api/movies/search")
    def search_movies(q: str = Query("", min_length=1), limit: int = Query(20, ge=1, le=50)):
        return {"items": catalog_service.search_movies(q, limit=limit)}

    @app.get("/api/movies/{movie_id}/ratings")
    def get_movie_ratings(movie_id: int, limit: int = Query(8, ge=1, le=50), offset: int = Query(0, ge=0)):
        result = catalog_service.get_movie_rating_records(movie_id, limit=limit, offset=offset)
        if result is None:
            raise HTTPException(status_code=404, detail="Movie not found")
        return result

    @app.get("/api/movies/{movie_id}")
    def get_movie(movie_id: int):
        movie = catalog_service.get_movie_detail(movie_id)
        if movie is None:
            raise HTTPException(status_code=404, detail="Movie not found")
        return movie

    @app.get("/api/users/{user_id}/history")
    def user_history(user_id: int):
        return {"items": catalog_service.get_user_history(user_id)}

    @app.get("/api/users/{user_id}/ratings/{movie_id}")
    def get_user_movie_rating(user_id: int, movie_id: int):
        rating = catalog_service.get_user_movie_rating(user_id, movie_id)
        if rating is None:
            raise HTTPException(status_code=404, detail="Rating not found")
        return rating

    @app.post("/api/users/{user_id}/ratings")
    def create_user_rating(user_id: int, payload: RatingPayload):
        try:
            rating = catalog_service.save_user_rating(user_id, payload.movie_id, payload.rating, payload.comment)
            recommendation_service.record_rating(user_id, payload.movie_id, payload.rating)
            return rating
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.put("/api/users/{user_id}/ratings/{movie_id}")
    def update_user_rating(user_id: int, movie_id: int, payload: RatingPayload):
        try:
            rating = catalog_service.save_user_rating(user_id, movie_id, payload.rating, payload.comment)
            recommendation_service.record_rating(user_id, movie_id, payload.rating)
            return rating
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.delete("/api/users/{user_id}/ratings/{movie_id}")
    def delete_user_rating(user_id: int, movie_id: int):
        deleted = catalog_service.delete_user_rating(user_id, movie_id)
        recommendation_service.delete_rating(user_id, movie_id)
        return {"deleted": deleted}

    @app.get("/api/users/{user_id}/preference-profile")
    def user_preference_profile(
        user_id: int,
        window: str = Query("all", pattern="^(all|year|quarter|month)$"),
    ):
        return catalog_service.get_user_preference_profile(user_id, window=window)

    @app.get("/api/recommendations/{user_id}")
    def get_recommendations(
        user_id: int,
        algorithm: str = Query("popularity"),
        limit: int = Query(10, ge=1, le=50),
    ):
        try:
            return recommendation_service.recommend(user_id=user_id, algorithm=algorithm, limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/metrics/models")
    def model_metrics():
        return {"items": catalog_service.get_model_metrics()}

    @app.get("/api/metrics/ablation")
    def ablation_metrics():
        return {"items": catalog_service.get_ablation_results()}

    return app


if FastAPI is not None:
    app = build_app()
else:
    app = None


if __name__ == "__main__":
    if FastAPI is None:
        print("FastAPI is not installed. Please install dependencies first.")
    else:
        print("Run with: uvicorn app.main:app --reload")

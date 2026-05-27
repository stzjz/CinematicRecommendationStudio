# 后端设计说明

## 目标

先提供一组稳定、通用、适合前端联调的接口，后续无缝替换成真实推荐模型结果。

当前已实现两种数据来源：
- `memory`：内存样例数据，适合快速演示
- `sqlite`：真实本地数据库，适合后续接入 MovieLens 清洗结果

## 推荐算法分层

- `popularity`
  - 适合冷启动和演示兜底
  - 基于全局平均分和评分人数排序
- `user_cf`
  - 基于用户评分重叠构建相似度
  - 能体现个性化推荐的基本思路
- `content_based`
  - 基于用户已喜欢电影的类型偏好做推荐
  - 方便在 UI 上展示“为什么推荐给你”

后续新增深度模型时，沿用同一个接口即可：
- `neumf`
- `lightgcn`

## API 草案

### `GET /api/health`
返回服务健康状态，同时带上当前数据源和数据库路径，便于排查联调问题。

### `GET /api/users`
返回可选用户列表，用于前端伪登录或切换用户。

### `GET /api/movies/hot?limit=10`
返回热门电影，用于首页推荐区。

### `GET /api/movies/{movie_id}`
返回电影详情。

### `GET /api/users/{user_id}/history`
返回用户历史评分记录。

### `GET /api/recommendations/{user_id}?algorithm=popularity&limit=10`
返回统一结构的推荐结果。

### `GET /api/metrics/models`
返回模型对比指标。

### `GET /api/metrics/ablation`
返回消融实验结果。

## 统一响应示例

```json
{
  "user_id": 1,
  "algorithm": "user_cf",
  "items": [
    {
      "movie_id": 6,
      "title": "Interstellar",
      "genres": ["Sci-Fi", "Drama"],
      "score": 4.82,
      "reason": "与你相似的用户对这部电影评分较高"
    }
  ],
  "meta": {
    "candidate_count": 3,
    "description": "User-based collaborative filtering baseline"
  }
}
```

## 数据库落地建议

建议至少维护以下表：
- `users`
- `movies`
- `ratings`
- `recommendations`
- `model_metrics`
- `ablation_results`
- `training_logs`

当前代码先用内存样例数据跑通，后续可切换为 MySQL 或 SQLite。

## 当前 SQLite 流程

1. 使用 `backend/sql/schema_sqlite.sql` 初始化数据库
2. 用 `backend/scripts/init_sqlite.py` 导入样例数据
3. API 启动时通过 repository 层读取 SQLite
4. 推荐算法层继续消费统一的 `users / movies / ratings` 数据结构

这意味着后续替换成真实数据时，只要把导入脚本换成 MovieLens 清洗结果导入即可，不需要改接口层。

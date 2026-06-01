# CinematicRecommendationStudio

一个面向课程答辩展示的电影推荐系统项目骨架。当前重点是先把前后端联调用的基础设施搭好：统一接口、简单推荐基线、数据库 schema、开发文档和后续可替换的算法接入层。

## 当前目录

```text
CinematicRecommendationStudio/
├── README.md
├── docs/
│   ├── backend_design.md
│   └── experiment_plan.md
├── backend/
│   ├── app/
│   ├── data/
│   ├── scripts/
│   ├── sql/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
└── 第六章 推荐系统实践.pptx
```

## 已完成内容

- 把原来的项目说明迁移到 `docs/experiment_plan.md`
- 新建后端原型，统一了推荐接口结构
- 实现 3 个可直接作为比较基线的推荐算法
  - `popularity`: 热门推荐
  - `user_cf`: 基于用户的协同过滤
  - `content_based`: 基于类型标签的内容推荐
- 补充了数据库 schema 草案
- 打通了 `SQLite` 数据源加载与初始化脚本
- 新建了 `React + Vite` 前端项目，并接入现有推荐接口
- 补充了基础测试用例和后端设计文档

## 推荐接口设计

推荐接口统一为：

- `GET /api/recommendations/{user_id}?algorithm=popularity&limit=10`

返回结构统一包含：
- `algorithm`: 算法标识
- `items`: 推荐列表
- `reason`: 推荐理由
- `score`: 排序分数
- `meta`: 算法说明和可扩展字段

这样后续接入 `NeuMF`、`LightGCN` 时，前端不用改接口消费方式，只需要切换算法名。

## 环境配置

后端建议使用项目内的 `.venv`，避免污染全局 Python 环境：

```bash
cd CinematicRecommendationStudio
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

前端需要 `Node.js 20+`。如果本机没有 Node，可以将官方二进制解压到项目内的 `.tools/node`，避免安装到全局环境。以下示例适用于 macOS Apple Silicon：

```bash
mkdir -p .tools
curl -fsSL https://nodejs.org/dist/v24.15.0/node-v24.15.0-darwin-arm64.tar.gz \
  -o /tmp/node-v24.15.0-darwin-arm64.tar.gz
tar -xzf /tmp/node-v24.15.0-darwin-arm64.tar.gz -C .tools
mv .tools/node-v24.15.0-darwin-arm64 .tools/node
export PATH="$PWD/.tools/node/bin:$PATH"
```

`.venv`、`.tools`、`node_modules`、构建产物和本地数据库均已加入 `.gitignore`。

## 启动后端

首次运行时初始化 SQLite 数据库：

```bash
cd CinematicRecommendationStudio/backend
../.venv/bin/python scripts/init_sqlite.py
```

初始化后会生成默认数据库文件：
- `backend/data/app.db`

启动后端：

```bash
cd CinematicRecommendationStudio/backend
../.venv/bin/uvicorn app.main:app --reload
```

启动后可直接打开：
- `http://127.0.0.1:8000/`：后端自带演示界面
- `http://127.0.0.1:8000/docs`：Swagger API 文档

接口地址：
- `/api/health`
- `/api/movies/hot`
- `/api/users`
- `/api/recommendations/{user_id}`
- `/api/metrics/models`

## 启动前端

前端使用 `React + Vite`，开发时通过代理把 `/api` 转发到 `127.0.0.1:8000`。

如果使用项目内 Node，先在项目根目录将它加入当前终端的 `PATH`：

```bash
export PATH="$PWD/.tools/node/bin:$PATH"
```

使用锁文件安装依赖：

```bash
cd frontend
npm ci
```

启动开发服务器：

```bash
npm run dev -- --host 0.0.0.0
```

默认访问：
- `http://127.0.0.1:5173/`

如果代理环境有问题，也可以显式指定后端地址：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api npm run dev -- --host 0.0.0.0
```

后端已经允许这些常见前端来源跨域访问：
- `http://127.0.0.1:5173`
- `http://localhost:5173`
- `http://127.0.0.1:3000`
- `http://localhost:3000`

生产构建：

```bash
npm run build
```

当前前端已经接入这些后端接口：
- `/api/health`
- `/api/users`
- `/api/algorithms`
- `/api/movies/hot`
- `/api/recommendations/{user_id}`
- `/api/users/{user_id}/history`
- `/api/metrics/models`
- `/api/metrics/ablation`

## 数据源切换

默认策略：
- 如果 `backend/data/app.db` 存在，则自动使用 `SQLite`
- 如果数据库文件不存在，则回退到内存样例数据

也可以显式指定：

```bash
cd CinematicRecommendationStudio/backend
RECSYS_DATA_SOURCE=sqlite RECSYS_DB_PATH="$PWD/data/app.db" ../.venv/bin/uvicorn app.main:app --reload
```

支持的 `RECSYS_DATA_SOURCE`：
- `auto`
- `sqlite`
- `memory`

## 数据库文件与 Schema

- SQLite schema: `backend/sql/schema_sqlite.sql`
- MySQL schema: `backend/sql/schema_mysql.sql`

当前已经先打通 `SQLite`，更适合本地开发和课程答辩演示；后续如果部署到 MySQL，可以继续沿用同一套接口层。

## 运行测试

```bash
cd CinematicRecommendationStudio/backend
../.venv/bin/python -m unittest discover -s tests -v
```

## 下一步建议

1. 先让前端按现有接口把页面骨架接起来。
2. 把 MovieLens 数据清洗后导入 `SQLite`，先跑通真实数据链路。
3. 用真实离线结果替换当前样例数据。
4. 再接入 `NeuMF` 和 `LightGCN` 作为正式模型。

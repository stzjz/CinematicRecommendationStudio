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

以下命令均从项目根目录执行。先进入项目：

```bash
cd CinematicRecommendationStudio
```

### 后端环境

使用项目内的 `.venv`，避免污染全局 Python 环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
```

不需要激活虚拟环境，后续命令会直接调用 `.venv/bin` 中的 Python 工具。

### 前端环境

前端需要 `Node.js 20+`。如果本机没有 Node，可以将官方二进制解压到项目内的 `.tools/node`，避免安装到全局环境。以下示例适用于 macOS Apple Silicon：

```bash
mkdir -p .tools
curl -fsSL https://nodejs.org/dist/v24.15.0/node-v24.15.0-darwin-arm64.tar.gz \
  -o /tmp/node-v24.15.0-darwin-arm64.tar.gz
tar -xzf /tmp/node-v24.15.0-darwin-arm64.tar.gz -C .tools
mv .tools/node-v24.15.0-darwin-arm64 .tools/node
```

安装前端依赖：

```bash
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend ci
```

如果本机已经全局安装了 `Node.js 20+`，也可以直接运行 `npm --prefix frontend ci`。

`.venv`、`.tools`、`node_modules`、构建产物和本地数据库均已加入 `.gitignore`。

## 数据库初始化

项目使用 `SQLite`，数据库文件位于 `backend/data/app.db`。

### 导入 MovieLens-1M

项目支持将 MovieLens-1M 的用户、电影和评分数据导入 SQLite。将数据集压缩包放在 `backend/data/raw/ml-1m.zip`，不需要手动解压。

如果本地还没有压缩包，可以从 GroupLens 下载：

```bash
mkdir -p backend/data/raw
curl -fL https://files.grouplens.org/datasets/movielens/ml-1m.zip \
  -o backend/data/raw/ml-1m.zip
```

执行导入：

```bash
.venv/bin/python backend/scripts/import_movielens.py
```

MovieLens-1M 导入后包含：
- `6,040` 个用户
- `3,883` 部电影
- `1,000,209` 条评分

### 使用演示样例

如需快速恢复为内置演示数据，可以运行：

```bash
.venv/bin/python backend/scripts/init_sqlite.py
```

该命令会创建包含 `3` 个用户、`24` 部电影和 `31` 条评分的轻量样例库。

## 启动项目

后端和前端需要分别在两个终端中启动。两个终端都先进入项目根目录：

```bash
cd CinematicRecommendationStudio
```

### 启动后端

在第一个终端运行：

```bash
.venv/bin/uvicorn app.main:app --app-dir backend --reload
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

### 启动前端

前端使用 `React + Vite`，开发时通过代理把 `/api` 转发到 `127.0.0.1:8000`。

在第二个终端运行：

```bash
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run dev -- --host 0.0.0.0
```

默认访问：
- `http://127.0.0.1:5173/`

如果 `5173` 端口已被占用，Vite 会自动尝试 `5174` 等其他端口。请以终端输出的 `Local` 地址为准。可以使用以下命令检查端口占用：

```bash
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

如果出现 `zsh: command not found: npm`，请确认命令是在项目根目录执行，并检查本地 Node 是否存在：

```bash
ls .tools/node/bin/node
```

如果代理环境有问题，也可以显式指定后端地址：

```bash
PATH="$PWD/.tools/node/bin:$PATH" \
  VITE_API_BASE_URL=http://127.0.0.1:8000/api \
  npm --prefix frontend run dev -- --host 0.0.0.0
```

后端已经允许这些常见前端来源跨域访问：
- `http://127.0.0.1:5173`
- `http://localhost:5173`
- `http://127.0.0.1:3000`
- `http://localhost:3000`

生产构建：

```bash
PATH="$PWD/.tools/node/bin:$PATH" npm --prefix frontend run build
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

## 临时公网访问

课程答辩或临时演示时，可以使用 [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/) 将本地前端映射为公网 HTTPS 地址。外部请求会经过 Cloudflare 加密隧道转发到本机 Vite 服务，不需要公网 IP、路由器端口映射或开放入站端口。

保持前端和后端服务运行，在第三个终端中执行：

```bash
cloudflared tunnel --url http://127.0.0.1:5173
```

终端会输出类似以下地址：

```text
https://random-name.trycloudflare.com
```

手机或其他设备直接打开该 HTTPS 地址即可。如果 Vite 实际使用 `5174` 等其他端口，请同步修改 `cloudflared` 命令中的端口。

### 实验室服务器

实验室服务器即使没有公网 IP，也可以使用相同方式建立隧道。服务器需要允许主动访问外网，并满足以下条件：

- 可以正常解析域名。
- 防火墙允许出站连接。
- 优先允许出站 `TCP/UDP 7844`。
- 如果 UDP 受限，可以显式使用 HTTP/2：

```bash
cloudflared tunnel --protocol http2 --url http://127.0.0.1:5173
```

### 安全注意事项

- Quick Tunnel 仅适合临时测试和课程展示，不适合长期生产部署。
- 隧道运行期间，任何获得随机网址的人都可以访问页面和当前公开的 `/api` 接口。
- 只暴露前端端口，不要暴露 SSH、数据库端口或整个目录。
- 不要在演示数据库中保存密码、真实个人信息或隐私数据。
- 展示结束后，在前端、后端和 `cloudflared` 三个终端中分别按 `Ctrl+C`。
- 长期公开部署时，应使用正式 Tunnel、固定域名、身份认证和限流。

Quick Tunnel 的官方说明见：[TryCloudflare](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)。

## 数据源切换

默认策略：
- 如果 `backend/data/app.db` 存在，则自动使用 `SQLite`
- 如果数据库文件不存在，则回退到内存样例数据

也可以显式指定：

```bash
RECSYS_DATA_SOURCE=sqlite \
  RECSYS_DB_PATH="$PWD/backend/data/app.db" \
  .venv/bin/uvicorn app.main:app --app-dir backend --reload
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
cd backend
../.venv/bin/python -m unittest discover -s tests -v
```

## 下一步建议

1. 先让前端按现有接口把页面骨架接起来。
2. 把 MovieLens 数据清洗后导入 `SQLite`，先跑通真实数据链路。
3. 用真实离线结果替换当前样例数据。
4. 再接入 `NeuMF` 和 `LightGCN` 作为正式模型。

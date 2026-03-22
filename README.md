# FocusLedger

FocusLedger 是一个面向中文公众号信息流的本地研究与日报工具。

它当前聚焦四件事：
- 管理关注来源
- 同步文章内容到本地知识库
- 用 LLM 生成摘要和标签
- 按指定日期生成日报，并支持通过 QClaw 在微信里调取日报

## 当前阶段能做什么

- 公众号来源管理
  - 新增、编辑、删除来源
  - 多级分组
  - 多标签
- 文章同步
  - 按来源同步历史内容
  - 按页数和近几天范围控制同步
  - 自动去重
- 文章系统
  - 搜索、筛选、排序、分页
  - 时间区间筛选
  - 单篇删除、批量删除
  - 详情页查看摘要、正文、标签和原文链接
- 日报系统
  - 按日期生成日报
  - 按来源或来源分组限制日报范围
- QClaw 接入
  - 在微信里向 QClaw 请求某一天的日报

## 给组员的最快试用方式

如果只是想先把产品跑起来，不需要先装 Python、Node.js、PostgreSQL、Redis。

推荐最小依赖：
- Git
- Docker Desktop

### 1. 克隆项目

```powershell
git clone <你的-github-仓库地址>
cd FocusLedger
```

### 2. 启动整个项目

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\quick-start.ps1
```

这个脚本会做两件事：
- 如果没有 `.env`，自动从 `.env.example` 复制一份
- 直接用 Docker 启动 PostgreSQL、Redis、后端、前端

### 3. 打开页面

- 前端首页: [http://localhost:3000](http://localhost:3000)
- 来源管理: [http://localhost:3000/sources](http://localhost:3000/sources)
- 同步页: [http://localhost:3000/collect](http://localhost:3000/collect)
- 文章浏览: [http://localhost:3000/articles](http://localhost:3000/articles)
- 日报页: [http://localhost:3000/reports](http://localhost:3000/reports)

### 4. 检查服务状态

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\status.ps1
```

### 5. 查看前后端日志

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logs.ps1
```

### 6. 停止项目

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\quick-stop.ps1
```

## 页面说明

- `/sources`
  - 管理来源、分组、标签
- `/collect`
  - 配置来源、执行同步
- `/articles`
  - 浏览和筛选文章
- `/reports`
  - 生成日报
- `/status`
  - 查看系统状态

## 团队协作建议

如果你们是多人协作，建议按这个方式使用仓库：

- `main`
  - 始终保持可运行
- 每个开发者从 `main` 拉分支开发
- 完成后再合并回 `main`

建议的工作流：

```powershell
git checkout main
git pull
git checkout -b feature/your-feature-name
```

## 环境变量

项目根目录有一份模板：
- `.env.example`

第一次启动时，`scripts/quick-start.ps1` 会自动生成 `.env`。

默认情况下，即使不配置 LLM Key，系统也能运行，只是会退化到规则模式。

### 常用配置

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

APP_NAME=FocusLedger
ENVIRONMENT=development
API_PREFIX=/api/v1

DATABASE_URL=postgresql+psycopg://focusledger:focusledger@localhost:5432/focusledger
REDIS_URL=redis://localhost:6379/0

AUTO_CREATE_SCHEMA=true
ALLOW_CORS_ORIGINS=http://localhost:3000
ARTICLE_STORAGE_PATH=backend/data/articles

LLM_PROVIDER=rule
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1

QCLAW_INTEGRATION_KEY=
```

### DeepSeek 配置示例

如果你要启用基于 OpenAI 格式的模型接口，可以这样配置：

```env
LLM_PROVIDER=openai_compatible
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

## 本地开发模式

如果你不是“试用”，而是要参与开发，推荐下面这套环境：

- Python 3.12+
- Node.js 20+
- Docker Desktop

### 1. 启动 PostgreSQL 和 Redis

```powershell
docker compose up -d postgres redis
```

### 2. 启动后端

```powershell
cd backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

## QClaw 接入

QClaw 是可选能力，不是项目运行的前置条件。

### 当前已实现的能力

- 在微信里向 QClaw 请求某一天的日报

### 调用链路

```text
微信 -> QClaw -> 本地 skill -> FocusLedger API -> 日报文本 -> QClaw -> 微信
```

### 关键文件

- QClaw skill 开发目录:
  - `qclaw-skills/focusledger-daily-report`
- QClaw 接口:
  - `backend/src/api/routes/qclaw.py`
  - `backend/src/services/qclaw.py`

### 使用前提

如果要通过微信远程请求日报，本机需要同时保持：
- QClaw 正在运行
- FocusLedger 后端正在运行

### 示例话术

```text
给我 2026-03-20 的日报
给我昨天的日报
给我前天的日报
```

## 目录结构

```text
backend/          FastAPI 后端
frontend/         Next.js 前端
scripts/          一键启动与运维脚本
qclaw-skills/     QClaw 自定义 skill
```

## 关键代码位置

这些目录建议始终纳入 git 跟踪：

- 后端接口与服务
  - `backend/src/api/routes`
  - `backend/src/services`
- 数据模型
  - `backend/src/models`
  - `backend/alembic/versions`
- 前端页面与组件
  - `frontend/app`
  - `frontend/components`
  - `frontend/lib`
- 启动与集成脚本
  - `scripts`
  - `qclaw-skills`
- 配置与文档
  - `.env.example`
  - `docker-compose.yml`
  - `README.md`

## 默认不应提交的内容

仓库已经通过 `.gitignore` 排除了这些本地内容：

- `.env`
- `node_modules`
- `.next`
- 日志文件
- 本地数据目录
- 本地虚拟环境
- SQLite / DB 文件

上传到 GitHub 前，确认不要手动提交这些内容。

## 常见问题

### 1. 页面打不开

先检查容器状态：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\status.ps1
```

再检查健康接口：

```powershell
curl http://localhost:8000/api/v1/health
```

### 2. 没有配置 LLM Key 能不能用

可以。

系统会退化到规则模式，仍然可以：
- 管理来源
- 同步文章
- 浏览文章
- 生成基础日报

只是摘要、标签和日报质量会不如启用 LLM 时好。

### 3. 组员只想试产品，不想配开发环境

就按“最快试用方式”走：
- 安装 Git
- 安装 Docker Desktop
- 运行 `scripts/quick-start.ps1`

### 4. 组员要参与开发

再额外安装：
- Python 3.12+
- Node.js 20+

然后按“本地开发模式”启动。

## 当前版本定位

这个仓库现在可以作为一个可共享的 Phase 1 版本来使用，覆盖：
- 来源管理
- 内容同步
- 文章浏览
- 日报生成
- QClaw 日报调用

下一阶段再继续考虑：
- 后端常驻化
- 更细的日报交互
- 更强的来源管理
- 更完整的团队协作和部署方案

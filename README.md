# FocusLedger

<p align="center">
  <img src="./frontend/public/favicon.svg" alt="FocusLedger" width="145" height="145" />
</p>


<p align="center">
  面向微信公众号文章的本地研究与内容生产工作台
</p>

<p align="center">
  <img alt="Next.js 15" src="https://img.shields.io/badge/Next.js-15-111111?style=flat-square&logo=nextdotjs&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-0f766e?style=flat-square&logo=fastapi&logoColor=white" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-16-1d4ed8?style=flat-square&logo=postgresql&logoColor=white" />
  <img alt="Redis" src="https://img.shields.io/badge/Redis-7-b91c1c?style=flat-square&logo=redis&logoColor=white" />
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5-1d4ed8?style=flat-square&logo=typescript&logoColor=white" />
  <img alt="Tailwind CSS" src="https://img.shields.io/badge/Tailwind_CSS-4-0891b2?style=flat-square&logo=tailwindcss&logoColor=white" />
</p>

<p align="center">
  来源管理 · 文章沉淀 · LLM 总结 · Notebook 研究 · 播客脚本 · 音频生成 · Agent 协作
</p>

FocusLedger 是一个运行在本地的微信公众号文章研究平台。它的核心目标，是把已经进入本地的公众号文章组织成可检索、可总结、可研究、可生成内容的知识资产。

当前项目重点是三件事：

- 建立稳定的本地文章库与来源管理体系
- 提供围绕专题研究的 Notebook 工作区
- 提供一组面向外部 AI agent 的任务型接口与本地 skill

## 产品能力

### 文章库

- 管理公众号来源、主页链接与凭据状态
- 通过历史同步或文章链接直入库沉淀内容
- 支持搜索、收藏、标签、批量 LLM 总结
- 支持按来源、标签、时间范围筛选文章

### Notebook

- 创建专题工作区并组织研究来源
- 基于 Notebook 发起 AI 问答
- 生成播客脚本
- 生成播客音频

### Agent 协作

- 提供面向任务的后端接口，而不是裸露底层 CRUD
- 支持文章导入、文章整理、Notebook 管理与 Notebook 输出
- 支持被本地 skill、脚本编排或其他 AI 工具调用

## 技术结构

- 前端：`frontend/`，Next.js 15 App Router + TypeScript + Tailwind CSS
- 后端：`backend/`，FastAPI + SQLAlchemy + Alembic
- TTS Worker：`tools/tts-worker/`，FastAPI + edge-tts / Tencent TTS
- 基础设施：PostgreSQL + Redis，通过 Docker Compose 运行

## 环境要求

- Python 3.12
- Node.js 22
- Docker Desktop

## Python 解释器约定

本项目统一使用：

- `backend\.venv\Scripts\python.exe`

## 快速开始

### 1. 克隆项目

```powershell
git clone <your-repo-url>
cd FocusLedger
```

### 2. 准备环境变量

```powershell
copy .env.example .env
```

至少确认这些配置可用：

```env
DATABASE_URL=postgresql+psycopg://focusledger:focusledger@localhost:15432/focusledger
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
TTS_WORKER_BASE_URL=http://localhost:8010
```

### 3. 安装后端依赖

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

如需使用 TTS worker，还需要安装 worker 依赖：

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r .\tools\tts-worker\requirements.txt
```

### 4. 安装前端依赖

```powershell
cd frontend
npm install
cd ..
```

### 5. 启动 PostgreSQL 和 Redis

```powershell
docker compose up -d postgres redis
```

本地数据目录位于：

- `data/postgres`
- `data/redis`

### 6. 初始化 / 升级数据库

第一次配置项目时，用这一步创建数据库表；后续拉取到包含新迁移的代码时，也要再次执行。

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
cd ..
```

### 7. 启动后端

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

### 9. 按需启动 TTS Worker

只有在测试播客音频或 agent 侧音频工作流时才需要启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tts-start.ps1
```

## 运行说明

推荐的日常入口：

- `/collect`：公众号凭据更新与历史文章同步
- `/articles/import`：单篇 / 多篇文章链接直入库
- `/articles`：文章搜索、收藏、标签与 LLM 总结
- `/notebooks`：专题研究工作区、问答、播客脚本与音频

默认地址：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`
- PostgreSQL：`localhost:15432`
- Redis：`localhost:6379`
- TTS Worker 健康检查：`http://localhost:8010/health`

输出目录：

- `data/postgres`
- `data/redis`
- `data/audio`

## Agent 集成

FocusLedger 当前提供一组面向外部 AI 工具的任务型接口，默认前缀为：

- `http://localhost:8000/api/v1/integrations/agent`

这组接口覆盖：

- 文章链接导入
- 文章搜索、标签整理、收藏更新与批量 LLM 总结
- Notebook 创建、更新、查询与加入文章
- 基于 Notebook 的问答、播客脚本生成与音频生成
- 播客脚本列表、脚本详情与音频状态查询

仓库内置了一套本地 skill：

- `agent-skills/focusledger-notebooklm/`

它的定位不是绑定某一个特定工具，而是作为 FocusLedger 面向外部 AI agent 的统一协作入口。只要目标工具支持本地 skill 或本地脚本调用，就可以复用这套能力。

### Agent 协作前置条件

最少需要先启动：

- PostgreSQL 与 Redis
- FocusLedger 后端

如果任务涉及播客音频，还需要额外启动：

- TTS Worker

如果任务涉及 Notebook 问答或播客脚本生成，还需要：

- 有效的 LLM 配置

如需开启接口鉴权，可在 `.env` 中配置：

```env
AGENT_INTEGRATION_KEY=your-secret-key
```

然后在对应 agent skill 的运行环境中同步设置同名环境变量。

## 关闭方式

### 1. 关闭前端

在前端终端中按：

```powershell
Ctrl + C
```

### 2. 关闭后端

在后端终端中按：

```powershell
Ctrl + C
```

### 3. 关闭 TTS Worker

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tts-stop.ps1
```

### 4. 关闭 Docker 基础设施

```powershell
docker compose stop postgres redis
```

如需连容器一起移除：

```powershell
docker compose down
```

## 关键目录

- `frontend/app/`：前端页面
- `frontend/components/ui.tsx`：共享 UI 组件
- `frontend/lib/`：API / 类型 / React Query hooks
- `backend/src/api/routes/`：HTTP 路由
- `backend/src/services/`：业务逻辑层
- `backend/src/models/`：数据库模型
- `backend/src/schemas/`：Pydantic schema
- `backend/src/integrations/`：TTS / 微信集成
- `agent-skills/focusledger-notebooklm/`：通用 agent skill
- `tools/tts-worker/app.py`：TTS 服务主文件
- `docs/taxonomies/`：来源与文章 taxonomy 体系

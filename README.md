# FocusLedger

<p align="center">
  <img src="./frontend/public/favicon.svg" alt="FocusLedger" width="96" height="96" />
</p>

<p align="center">
  面向微信公众号文章的本地研究与内容整理工具
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
  来源管理 · 文章同步 · LLM 总结 · Notebook 对话 · 播客脚本 · 音频生成
</p>

FocusLedger 是一个运行在本地的微信公众号文章研究平台，核心围绕三件事展开：

- 管理公众号来源与手动凭据更新
- 建立本地文章库，支持筛选、收藏、标签与 LLM 总结
- 提供 Notebook 工作区，支持 AI 对话、播客脚本与音频生成

当前产品方向已经从“自动刷新公众号凭据”转向“充分利用已有公众号文章数据”，目标是逐步演进为一个基于微信公众号文章的 NotebookLM 型产品。

## 技术结构

- 前端：`frontend/`，Next.js 15 App Router + TypeScript + Tailwind CSS
- 后端：`backend/`，FastAPI + SQLAlchemy + Alembic
- TTS Worker：`tools/tts-worker/`，FastAPI + edge-tts
- 基础设施：PostgreSQL + Redis，通过 Docker Compose 运行

## 环境要求

- Python 3.12
- Node.js 22
- Docker Desktop
- Anaconda
  当前 TTS worker 默认使用 `D:\anaconda3\python.exe`

## 快速开始

第一次在一台新机器上配置 FocusLedger，按下面的顺序即可。

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

### 3. 安装前后端依赖

后端依赖：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

前端依赖：

```powershell
cd frontend
npm install
cd ..
```

### 4. 启动 PostgreSQL 和 Redis

```powershell
docker compose up -d postgres redis
```

数据库文件会直接保存在项目内目录：

- `data/postgres`
- `data/redis`

### 5. 初始化 / 升级数据库结构

第一次配置时，这一步用于创建项目需要的数据表。
后续如果拉取了新代码，而数据库结构有变化，也需要再次执行。

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
cd ..
```

### 6. 启动后端

```powershell
cd backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

### 8. 按需启动 TTS Worker

只有在测试 Notebook 音频功能时才需要启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tts-start.ps1
```

## 运行说明

项目只有一种运行方式：手动分步启动。

默认地址：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`
- PostgreSQL：`localhost:15432`
- Redis：`localhost:6379`
- TTS Worker 健康检查：`http://localhost:8010/health`

数据目录：

- `data/postgres`
- `data/redis`
- `data/audio`

## 关闭方式

项目也只有一种关闭方式：按组件分别关闭。

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

如果你启动过 TTS worker，再执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tts-stop.ps1
```

### 4. 关闭 Docker 基础设施

回到项目根目录执行：

```powershell
docker compose stop postgres redis
```

如果你需要连容器一起移除：

```powershell
docker compose down
```

## 常用路径

- 前端页面：`frontend/app/`
- 前端共享组件：`frontend/components/ui.tsx`
- 前端数据层：`frontend/lib/`
- 后端路由：`backend/src/api/routes/`
- 后端服务：`backend/src/services/`
- Notebook 相关模型：`backend/src/models/`
- TTS worker：`tools/tts-worker/app.py`
- taxonomy 文档：`docs/taxonomies/`

## 当前主要页面

- `/`：总览
- `/sources`：来源管理
- `/sources/add`：添加来源
- `/collect`：凭据更新与文章同步
- `/articles`：文章浏览
- `/articles/[id]`：文章详情
- `/notebooks`：Notebook 列表
- `/notebooks/[id]`：Notebook 工作区
- `/status`：系统状态

## 协作提示

- 不再提供快速启动脚本；请按 README 中的分步流程启动
- TTS worker 不是常驻必需服务，只在音频功能测试时启动
- 当前产品方向不再包含日报功能

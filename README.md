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

FocusLedger 是一个运行在本地的微信公众号文章研究平台，当前重点是：

- 管理公众号来源与手动凭据更新
- 建立本地文章库，支持筛选、收藏、标签与 LLM 总结
- 提供 Notebook 工作区，支持 AI 对话、播客脚本与音频生成

当前产品方向不再包含“日报”能力，也不再继续推进公众号凭据自动刷新。

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

不要混用：

- `D:\anaconda3\python.exe`
- 系统全局 `python`

推荐在 VS Code 中把当前工作区的 Python interpreter 也设置为：

```text
E:\Desktop\FocusLedger\backend\.venv\Scripts\python.exe
```

这只影响 FocusLedger 这个项目，不会影响你的其他项目。

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

如果你准备使用 TTS worker，还需要安装 worker 依赖：

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

数据目录位于：

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

推荐直接显式使用虚拟环境解释器：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

如需先激活虚拟环境，也可以这样：

```powershell
.\backend\.venv\Scripts\activate.ps1
cd backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

### 9. 按需启动 TTS Worker

只有在测试 Notebook 音频功能时才需要启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tts-start.ps1
```

## 运行说明

项目采用手动分步启动。

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

如果你启动过 TTS worker：

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

- 不提供一键“快速启动”脚本，请按 README 中的分步流程启动
- TTS worker 不是常驻必需服务，只在音频功能测试时启动
- 本项目统一使用 `backend/.venv` 作为 Python 运行环境
- 当前产品方向不再包含日报功能

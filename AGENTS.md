# FocusLedger — AI Agent 协作文档

> 本文档供 AI 编程助手（Claude Code、Codex CLI 等）阅读，用于理解项目背景、当前边界与协作规范。

---

## 1. 项目定位

FocusLedger 是一个**运行在本地的微信公众号文章研究平台**。

核心价值不在于"自动抓取最新文章"，而在于：

- 管理公众号来源与凭据同步流程
- 建立本地文章库（搜索、标签、收藏、LLM 总结）
- 提供 Notebook 工作区（AI 对话 + 播客脚本 + 音频生成）

---

## 2. 技术结构

### 前端
- **框架**：Next.js 15 App Router，TypeScript，Tailwind CSS
- **目录**：`frontend/`
- **共享组件**：`frontend/components/ui.tsx`（Shell, Sidebar, PageFrame, ActionButton 等）
- **数据层**：`frontend/lib/queries.ts`（React Query hooks），`frontend/lib/api.ts`，`frontend/lib/types.ts`

### 后端
- **框架**：FastAPI，SQLAlchemy（async），Alembic
- **目录**：`backend/src/`
- **分层**：`api/routes/` → `services/` → `models/` / `integrations/`
- **LLM**：`backend/src/llm/providers.py`，通过 `Settings.llm_provider` 切换

### TTS Worker
- **实现**：`tools/tts-worker/app.py`，FastAPI + edge-tts
- **端口**：`:8010`
- **运行方式**：本地 Python 进程（Anaconda，`D:\anaconda3\python.exe`），不走 Docker
- **启动**：按需手动执行 `scripts/tts-start.ps1`

### 基础设施
- PostgreSQL 16（`:5432`）、Redis 7（`:6379`），均通过 Docker Compose 运行
- `docker-compose.yml` — 仅用于启动基础设施服务（postgres, redis）
- 本地数据目录绑定到 `data/postgres` 与 `data/redis`
- 前端、后端、tts-worker 均以本地进程方式手动启动，不纳入 Docker

---

## 3. 当前正式能力边界

### 3.1 保留的同步能力

- 来源创建与 `__biz` 解析
- `profile_ext` 凭据保存与状态检测
- 凭据手动更新（用户在 `/collect` 页面操作）
- 后台文章同步任务（去重 + 正文入库）

### 3.2 已放弃的路径（不要重新引入）

- Fiddler Classic / FiddlerCore
- mitmproxy
- 自动读取抓包结果
- 自动刷新凭据
- 自研 Windows helper

### 3.3 Notebook 当前支持

- 新建 / 重命名 / emoji / 说明
- 文章加入与移出
- 单工作区单会话 AI 对话（消息持久化）
- 播客脚本生成（Brief / Explainer / Commentary）
- 播客音频生成（edge-tts，MP3 输出，voice + rate 可配置）

---

## 4. taxonomy 体系

三份本地文档约束 LLM 的分类输出，修改需谨慎：

| 文件 | 用途 |
|---|---|
| `docs/taxonomies/source-group-taxonomy.md` | 来源主分组 |
| `docs/taxonomies/source-tag-taxonomy.md` | 来源横向标签 |
| `docs/taxonomies/article-tag-taxonomy.md` | 文章主题标签与内容类型 |

---

## 5. 关键目录速查

```
backend/src/api/routes/         HTTP 路由（FastAPI）
backend/src/services/           业务逻辑层
backend/src/integrations/       微信采集 / tts_worker 客户端
backend/src/llm/                LLM provider 抽象
backend/src/models/             SQLAlchemy 模型
backend/src/schemas/            Pydantic 响应/请求 schema
backend/alembic/versions/       数据库迁移文件
frontend/app/                   Next.js 页面（App Router）
frontend/components/ui.tsx      全局 UI 组件库
frontend/lib/                   API / 类型 / React Query hooks
tools/tts-worker/app.py         TTS 服务主文件
scripts/                        启动 / 停止脚本
docs/taxonomies/                标签体系文档
```

---

## 6. 协作规范

### 改动前必须确认的核心链路

以下任何一条链路受影响，合并前必须手动验证：

1. 文章同步主链路（来源创建 → 凭据验证 → 同步 → 入库）
2. 文章 LLM 总结链路（单篇 + 批量）
3. Notebook AI 对话链路
4. 播客脚本生成链路
5. 播客音频生成链路（tts-worker 调用）

**最低验证标准**：前端可启动，`/articles`、`/sources`、`/collect`、`/notebooks` 可正常访问。

### 数据库迁移

- 每次新增或修改 Model 必须生成迁移文件：`alembic revision --autogenerate -m "描述"`
- 迁移文件纳入 Git

### 前端组件规范

- 所有页面使用 `PageFrame` 作为布局容器
- 共享 UI 仅在 `frontend/components/ui.tsx` 中维护
- 颜色系统基于 CSS 变量（`--bg`、`--accent`、`--accent2` 等），不硬编码颜色值

### TTS Worker

- 输出格式固定为 MP3（`format="mp3"`）
- 默认 voice：`zh-CN-XiaoxiaoNeural`
- 默认 rate：`-8%`
- 不引入任何依赖 GPU 的本地 TTS 方案

---

## 7. 环境变量关键配置

```env
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
TTS_WORKER_BASE_URL=http://localhost:8010
TTS_WORKER_TIMEOUT_SECONDS=60
TTS_AUDIO_OUTPUT_PATH=data/audio
```

---

## 8. 不纳入 Git 的内容

`.env` · 本地日志 · `data/` · `_ref_Access_wechat_article/` · `.claude/`

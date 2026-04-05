# FocusLedger — AI Agent 协作文档

> 本文档供 AI 编程助手（Claude Code、Codex CLI 等）阅读，用于理解项目背景、当前边界与协作规范。

---

## 1. 项目定位

FocusLedger 是一个运行在本地的微信公众号文章研究平台。

核心价值不在于“自动抓取最新文章”，而在于：

- 管理公众号来源与凭据同步流程
- 建立本地文章库（搜索、标签、收藏、LLM 总结）
- 提供 Notebook 工作区（AI 对话 + 播客脚本 + 音频生成）

---

## 2. 技术结构

### 前端

- 框架：Next.js 15 App Router，TypeScript，Tailwind CSS
- 目录：`frontend/`
- 共享组件：`frontend/components/ui.tsx`
- 数据层：`frontend/lib/queries.ts`、`frontend/lib/api.ts`、`frontend/lib/types.ts`

### 后端

- 框架：FastAPI，SQLAlchemy（async），Alembic
- 目录：`backend/src/`
- 分层：`api/routes/` → `services/` → `models/` / `integrations/`
- LLM：`backend/src/llm/providers.py`

### TTS Worker

- 实现：`tools/tts-worker/app.py`，FastAPI + edge-tts / Tencent TTS
- 端口：`:8010`
- 运行方式：本地 Python 进程，不走 Docker
- 启动：按需手动执行 `scripts/tts-start.ps1`

### Python 解释器约定

本项目统一使用：

- `backend\.venv\Scripts\python.exe`

不要混用：

- `D:\anaconda3\python.exe`
- 系统全局 `python`

如果在 VS Code 中工作，当前工作区的 interpreter 也应设置为：

- `E:\Desktop\FocusLedger\backend\.venv\Scripts\python.exe`

### 基础设施

- PostgreSQL 16、Redis 7，均通过 Docker Compose 运行
- `docker-compose.yml` 仅用于基础设施
- 本地数据目录绑定到 `data/postgres` 与 `data/redis`

---

## 3. 当前正式能力边界

### 3.1 保留的同步能力

- 来源创建与 `__biz` 解析
- `profile_ext` 凭据保存与状态检测
- 凭据手动更新（用户在 `/collect` 页面操作）
- 后台文章同步任务（去重 + 正文入库）

### 3.2 已放弃的路径

不要重新引入：

- Fiddler Classic / FiddlerCore
- mitmproxy
- 自动读取抓包结果
- 自动刷新凭据
- 自研 Windows helper
- 日报链路

### 3.3 Notebook 当前支持

- 新建 / 重命名 / emoji / 说明
- 文章加入与移出
- 单工作区单会话 AI 对话
- 播客脚本生成（Brief / Explainer / Commentary）
- 播客音频生成（edge-tts / Tencent TTS）

---

## 4. taxonomy 体系

三份本地文档约束 LLM 的分类输出：

| 文件 | 用途 |
|---|---|
| `docs/taxonomies/source-group-taxonomy.md` | 来源主分组 |
| `docs/taxonomies/source-tag-taxonomy.md` | 来源横向标签 |
| `docs/taxonomies/article-tag-taxonomy.md` | 文章主题标签与内容类型 |

---

## 5. 关键目录速查

```text
backend/src/api/routes/         HTTP 路由
backend/src/services/           业务逻辑层
backend/src/integrations/       微信采集 / tts_worker 客户端
backend/src/llm/                LLM provider 抽象
backend/src/models/             SQLAlchemy 模型
backend/src/schemas/            Pydantic schema
backend/alembic/versions/       数据库迁移文件
frontend/app/                   Next.js 页面
frontend/components/ui.tsx      全局 UI 组件
frontend/lib/                   API / 类型 / React Query hooks
tools/tts-worker/app.py         TTS 服务主文件
scripts/                        启动 / 停止脚本
docs/taxonomies/                taxonomy 文档
```

---

## 6. 协作规范

### 改动前必须确认的核心链路

以下任何链路受影响，合并前必须手动验证：

1. 文章同步主链路
2. 文章 LLM 总结链路（单篇 + 批量）
3. Notebook AI 对话链路
4. 播客脚本生成链路
5. 播客音频生成链路

最低验证标准：

- 前端可启动
- `/articles`、`/sources`、`/collect`、`/notebooks` 可正常访问

### 数据库迁移

- 新增或修改 Model 时必须生成迁移文件
- 迁移文件纳入 Git

### 前端组件规范

- 所有页面使用 `PageFrame`
- 共享 UI 在 `frontend/components/ui.tsx` 中维护
- 颜色系统基于 CSS 变量，不硬编码散乱颜色

### TTS Worker

- 默认输出 MP3
- 默认 voice：`zh-CN-XiaoxiaoNeural`
- 默认 rate：`-8%`
- 不引入依赖 GPU 的本地 TTS 方案

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
TTS_DISABLE_PROXY=false
TTS_HTTP_PROXY=http://127.0.0.1:7890
TTS_HTTPS_PROXY=http://127.0.0.1:7890
```

---

## 8. 不纳入 Git 的内容

`.env` · 本地日志 · `data/` · `_ref_Access_wechat_article/` · `.claude/`

# FocusLedger

FocusLedger 是一个面向中文微信公众号信息流的本地研究工具。

当前阶段的目标很明确：
- 管理公众号来源
- 采集公众号历史文章
- 对文章做结构化摘要和标签分析
- 浏览、筛选、删除文章
- 按指定日期生成日报
- 通过 QClaw 在微信里直接请求某一天的日报

## 当前能力

### 1. 公众号来源管理
- 新增、编辑、删除公众号来源
- 支持多级分组，格式如 `投研/宏观/中国`
- 支持多标签
- 来源和采集页分离：
  - `/sources` 负责管理来源
  - `/collect` 负责公众号主页解析、来源创建和文章同步

### 2. 微信公众号采集
- 采集流程参考并适配 [`yeximm/Access_wechat_article`](https://github.com/yeximm/Access_wechat_article)
- 支持从公众号文章链接提取主页链接
- 支持使用 Fiddler 抓取 `mp.weixin.qq.com/mp/profile_ext?...` token 链接
- 支持按来源同步历史文章
- 支持自定义同步页数和近几天范围
- 支持重复文章去重

### 3. 文章系统
- 文章浏览页支持：
  - 总文章数
  - 关键词搜索
  - 来源筛选
  - 时间区间筛选
  - 排序
  - 分页
  - 单篇删除
  - 批量删除
- 文章详情页支持：
  - 原文链接
  - 公众号信息
  - LLM 摘要
  - 正文展示
  - 文章标签

### 4. LLM 分析
- 支持规则模式和 OpenAI-compatible 模式
- 已适配 DeepSeek 这类 OpenAI 格式接口
- 新采集文章会执行：
  - 摘要生成
  - 正文轻度排版
  - 主题标签
  - 实体标签
  - 内容类型识别

### 5. 日报系统
- 支持按指定日期生成日报
- 支持按来源或来源分组限制范围
- 日报会综合：
  - 来源分组
  - 来源标签
  - 文章摘要
  - 文章标签
- Web 页面入口：
  - `/reports`
- API：
  - `GET /api/v1/reports/daily`

### 6. QClaw 接入
- 已实现通过 QClaw 在微信里请求日报
- 当前只开放一项能力：
  - 获取某个日期的日报
- 已新增 QClaw 专用接口：
  - `GET /api/v1/integrations/qclaw/daily-report`
- 已提供本地 skill：
  - [qclaw-skills/focusledger-daily-report](E:/Desktop/FocusLedger/qclaw-skills/focusledger-daily-report)

## 技术栈

### 前端
- Next.js 15
- TypeScript
- Tailwind CSS

### 后端
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Redis

### LLM
- Rule-based fallback
- OpenAI-compatible API

## 目录结构

```text
frontend/                     Next.js 前端
backend/                      FastAPI 后端
backend/src/api/routes/       API 路由
backend/src/services/         业务服务
backend/src/integrations/     微信采集适配层
qclaw-skills/                 QClaw 技能
docker-compose.yml            本地依赖启动
.env.example                  环境变量示例
```

## 环境准备

建议环境：
- Windows
- Docker Desktop
- Python 3.11+
- Node.js 20+

推荐使用 Docker 启动依赖：
- PostgreSQL
- Redis

## 环境变量

先复制环境变量模板：

```powershell
copy .env.example .env
```

最少需要确认这些配置：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

DATABASE_URL=postgresql+psycopg://focusledger:focusledger@localhost:5432/focusledger
REDIS_URL=redis://localhost:6379/0

LLM_PROVIDER=openai_compatible
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

QCLAW_INTEGRATION_KEY=
```

说明：
- 不配 `OPENAI_API_KEY` 也能运行，但会退化为规则模式
- 如果启用 `QCLAW_INTEGRATION_KEY`，QClaw 调用日报接口时也需要带同样的 key

## 本地启动

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

### 4. 访问

- 前端首页：`http://localhost:3000`
- 来源管理：`http://localhost:3000/sources`
- 采集页：`http://localhost:3000/collect`
- 文章浏览：`http://localhost:3000/articles`
- 日报页：`http://localhost:3000/reports`
- 健康检查：`http://localhost:8000/api/v1/health`

## 公众号采集流程

当前推荐流程：

1. 在 `/collect` 输入一篇真实公众号文章链接
2. 提取公众号主页链接
3. 在微信 PC 中打开主页链接
4. 使用 Fiddler 抓取 `mp.weixin.qq.com/mp/profile_ext?...`
5. 将该链接作为来源保存
6. 对该来源执行同步

说明：
- 当前项目按 `Access_wechat_article` 的方法获取公众号历史文章
- 来源一旦配置好，后续一般只需要继续同步，不需要每次重新抓 Fiddler
- 只有 token 失效时，才需要重新抓一次

## QClaw 接入说明

当前接入方式：
- QClaw 作为微信聊天入口
- FocusLedger 后端负责生成日报
- QClaw skill 负责调用本地 FocusLedger API

调用链路：

```text
微信 -> QClaw -> 本地 skill -> FocusLedger API -> 日报文本 -> QClaw -> 微信
```

### Skill 目录

项目内开发目录：
- [qclaw-skills/focusledger-daily-report](E:/Desktop/FocusLedger/qclaw-skills/focusledger-daily-report)

QClaw 安装目录：
- [focusledger-daily-report](E:/QClaw/resources/openclaw/config/skills/focusledger-daily-report)

### 使用前提

要想远程通过微信使用日报功能，本机至少要保持：
- QClaw 正在运行
- FocusLedger 后端正在运行

### 示例话术

```text
给我 2026-03-20 的日报
给我昨天的日报
给我前天的日报
```

后续可继续扩展：
- 详细版
- 原文链接
- 指定来源分组日报

## 已知边界

- 微信抓取依赖公众号 token 链接，本质上不是官方开放 API
- token 失效后需要重新抓取
- 富媒体内容目前主要按文本方式保留，不保留完整原始版式
- 当前 QClaw 接入只做“按日期获取日报”，不包含同步、文章搜索、来源管理等动作

## 当前阶段建议

如果你要把这个产品视为“初级阶段可交付版本”，现在已经可以覆盖：
- 公众号来源管理
- 公众号文章采集
- 文章浏览与筛选
- 指定日期日报
- 微信内通过 QClaw 获取日报

下一阶段再考虑：
- 后端常驻化
- 更稳的 token 失效处理
- QClaw 的详细版/原文链接交互
- 腾讯文档或文件形式分发完整版日报

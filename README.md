# FocusLedger

FocusLedger 是一个面向中文微信公众号文章的本地研究与内容整理工具。

当前阶段，它已经具备以下基础能力：

- 管理公众号来源
- 将文章同步到本地文章库
- 对文章做摘要、标签和结构化整理
- 生成指定日期的日报
- 通过 QClaw 在微信中调用日报

当前产品方向已经从“提升凭据自动刷新成功率”转向“充分利用已有公众号文章数据”，目标是逐步演进为一个基于微信公众号文章的 NotebookLM 型产品。

## 1. 当前产品判断

FocusLedger 目前最有价值的资产不是自动获取最新文章，而是已经沉淀下来的：

- 公众号来源管理能力
- 文章数据库
- 文章结构化处理能力
- 日报生成能力
- QClaw 集成经验

因此，当前主线重点是：

- 保持来源管理和文章同步可用
- 保留凭据状态检测和手动更新能力
- 围绕文章库、收藏、标签、工作区和 AI 助理能力继续发展

当前版本已经不再把 Fiddler 半自动刷新作为正式主流程。  
当凭据失效时，系统会明确提示用户手动更新 `profile_ext` 凭据，然后重新同步。

## 2. 当前技术结构

### 前端

- 技术栈：Next.js App Router
- 目录：`frontend/`
- 主要页面：
  - `/sources`
  - `/sources/add`
  - `/collect`
  - `/articles`
  - `/reports`
  - `/status`

### 后端

- 技术栈：FastAPI
- 目录：`backend/`
- 主要职责：
  - 来源管理
  - 文章同步与入库
  - 正文解析
  - 摘要与标签生成
  - 日报生成
  - QClaw 接口

### 基础设施

- PostgreSQL
- Redis
- Docker Compose

### QClaw

- 目录：`qclaw-skills/`
- 当前已完成：通过微信请求指定日期日报

## 3. 当前正式来源接入方式

### 3.1 来源创建

1. 用户提供一篇公众号文章链接
2. 系统解析 `__biz`
3. 系统生成公众号主页链接
4. 用户在微信 PC 中打开主页链接
5. 用户手动获取并保存一条 `profile_ext` 链接作为来源凭据
6. 后端后续使用这条凭据分页获取文章列表

### 3.2 凭据失效后的处理方式

来源凭据具有时效性，不是永久有效。

当前正式流程是：

1. 点击“同步文章”
2. 系统先验证当前凭据
3. 凭据有效：继续同步
4. 凭据失效：同步失败，并明确提示用户手动更新凭据
5. 用户在 `/collect` 页面粘贴新的 `profile_ext` 链接
6. 系统校验新凭据
7. 用户再次发起同步

这意味着，当前版本保留了：

- 凭据有效性检测
- 凭据状态展示
- 凭据手动更新
- 同步任务面板

不再保留：

- 自动启动 Fiddler
- 自动读取抓包结果
- 自动刷新凭据

## 4. 已完成功能

### 4.1 来源管理

- 新建来源
- 编辑来源
- 删除来源
- 多级分组
- 多标签

### 4.2 文章同步

- 支持按来源同步
- 支持起始页、结束页控制同步范围
- 支持按近几天过滤
- 支持文章去重
- 支持凭据验证
- 支持凭据手动更新
- 支持后台同步任务和任务进度面板

### 4.3 文章系统

- 文章浏览器
- 关键词搜索
- 来源筛选
- 时间区间筛选
- 排序与分页
- 单篇删除
- 批量删除
- 文章详情查看

### 4.4 内容结构化

- LLM 摘要
- LLM 标签
- 正文清洗与轻量整理

### 4.5 日报系统

- 按指定日期生成日报
- 支持按来源和来源分组缩小范围
- 汇总摘要、来源信息和标签信息

### 4.6 QClaw 集成

- 已支持通过微信请求指定日期日报

## 5. 下一阶段方向

产品方向见根目录文档：

- `PRODUCT_NOTEBOOKLM_DIRECTION.md`

当前重点不再是继续投入高不确定性的自动刷新链路，而是围绕已有公众号文章数据发展：

- 收藏管理
- 标签系统
- 工作区 / Notebook
- 基于工作区的问答与内容生成
- AI 助理式管理交互
- QClaw / Codex CLI / MCP 协同调用

## 6. 快速启动

### 6.1 试用环境

如果只是试用产品，推荐安装：

- Git
- Docker Desktop

#### 启动

```powershell
git clone <你的仓库地址>
cd FocusLedger
powershell -ExecutionPolicy Bypass -File .\scripts\quick-start.ps1
```

打开：

- 前端：http://localhost:3000
- 后端健康检查：http://localhost:8000/api/v1/health

#### 停止

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\quick-stop.ps1
```

### 6.2 开发环境

建议安装：

- Python 3.12
- Node.js 22
- Docker Desktop

#### 1. 复制环境变量

```powershell
copy .env.example .env
```

#### 2. 启动 PostgreSQL 和 Redis

```powershell
docker compose up -d postgres redis
```

#### 3. 启动后端

```powershell
cd backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

如果 `3000` 端口不可用：

```powershell
npm run dev:3300
```

## 7. 环境变量

`.env.example` 已给出基础示例。

常用配置项：

```env
DATABASE_URL=postgresql+psycopg://focusledger:focusledger@localhost:5432/focusledger
REDIS_URL=redis://localhost:6379/0

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ALLOW_CORS_ORIGINS=http://localhost:3000,http://localhost:3300

LLM_PROVIDER=rule
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_VERIFY_SSL=true
OPENAI_TIMEOUT_SECONDS=45
OPENAI_MAX_RETRIES=2

WECHAT_VERIFY_SSL=false
QCLAW_INTEGRATION_KEY=
```

## 8. 页面说明

### `/sources`

- 查看和管理来源
- 编辑来源信息
- 删除来源

### `/sources/add`

- 通过文章链接创建新来源
- 自动解析 `__biz`
- 自动生成主页链接

### `/collect`

- 验证凭据
- 手动更新凭据
- 设置同步参数
- 发起同步任务
- 查看最近任务结果

### `/articles`

- 搜索和筛选文章
- 查看文章详情
- 删除文章

### `/reports`

- 生成指定日期日报
- 按来源或来源分组缩小范围

## 9. 关键目录

- `backend/src/api/`
- `backend/src/services/`
- `backend/src/integrations/wechat_ingestion/`
- `backend/src/parsers/`
- `backend/src/llm/`
- `frontend/app/`
- `frontend/lib/`
- `qclaw-skills/`
- `scripts/`

## 10. 目录清理约定

建议纳入 Git 跟踪：

- 前后端代码
- README
- AGENTS.md
- 数据库迁移文件
- QClaw 技能
- 启动脚本
- 产品与架构文档

不应纳入 Git：

- `.env`
- 本地日志
- 本地缓存
- 临时导出文件
- `_ref_Access_wechat_article/`
- `.claude/`

## 11. 历史说明

这些技术路径已经被验证为不再作为主线继续投入：

- mitmproxy
- 自研 Windows helper（`.NET 8 + Titanium.Web.Proxy`）
- FiddlerCore
- Fiddler Classic 半自动刷新主流程

对应历史文档可以保留作参考，但当前实现和产品方向已经不再围绕这些路径推进。

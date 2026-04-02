# FocusLedger

FocusLedger 是一个面向中文微信公众号文章的本地研究与内容整理工具。

当前阶段，它的正式价值不在“自动抓取最新文章”，而在：

- 管理公众号来源并同步文章到本地文章库
- 基于文章数据做收藏、标签、筛选与专题整理
- 独立执行文章 LLM 总结与标签整理
- 基于文章库生成日报
- 逐步演进为一个基于微信公众号文章的 NotebookLM 型产品

## 当前产品判断

FocusLedger 现在最有价值的资产是：

- 已经入库的公众号文章数据
- 稳定可维护的来源管理与同步流程
- 文章管理层
- 标签体系与本地 taxonomy 文档
- 后续可以被 QClaw / MCP / AI 工具调用的内容整理能力

当前正式同步路径是：

1. 创建来源
2. 保存 `profile_ext` 凭据
3. 同步前验证凭据
4. 凭据有效则继续同步
5. 凭据失效则提示用户手动更新
6. 用户在 `/collect` 页面粘贴新的 `profile_ext`
7. 重新发起同步

自动刷新凭据、Fiddler callback、自动抓包等能力已经退出正式主链路。

## 当前阶段重点

当前开发重点是“阶段 A：打稳文章管理层”。

已经落地或正在强化的能力包括：

- 文章独立的 LLM 总结状态
- 文章收藏状态
- 单篇与批量文章 LLM 总结
- 基于筛选条件的批量总结
- 文章标签手动编辑
- 文章标签分层筛选
- 来源分组与来源标签编辑
- 来源 AI 分组与 AI 打标签
- 本地 taxonomy 文档约束来源与文章分类

## 当前能力边界

### 保留能力

- 来源创建与维护
- 公众号主页链接解析
- `profile_ext` 凭据保存
- 凭据状态检测
- 凭据手动更新
- 后台同步任务
- 文章去重与正文入库
- 文章独立 LLM 总结
- 来源 AI 分组与打标签

### 已降级或放弃的路径

- Fiddler Classic 半自动刷新主流程
- 自动读取抓包结果
- 自动刷新凭据
- FiddlerCore
- mitmproxy
- 自研 Windows helper

## taxonomy 体系

当前项目维护三份本地 taxonomy 文档：

- `docs/taxonomies/source-group-taxonomy.md`
- `docs/taxonomies/source-tag-taxonomy.md`
- `docs/taxonomies/article-tag-taxonomy.md`

这三份文档分别约束：

- 来源主分组
- 来源横向标签
- 文章主题标签与内容类型

设计原则：

- 分组只承担主归属
- 标签承担横向切片
- 文章标签、来源标签、来源分组分工明确
- 标签使用多级路径，父标签筛选应命中子标签
- taxonomy 优先稳定、高复用、可解释

## 前端页面

- `/sources`
  - 来源管理
  - 分组视图
  - 来源编辑
  - 来源 AI 分组与打标签

- `/sources/add`
  - 通过文章链接创建来源
  - 自动解析 `__biz`
  - 自动生成公众号主页链接

- `/collect`
  - 验证凭据
  - 手动更新凭据
  - 设置同步参数
  - 发起同步任务
  - 查看最近同步任务结果

- `/articles`
  - 搜索与筛选文章
  - 按文章标签筛选
  - 按总结状态筛选
  - 按收藏状态筛选
  - 批量总结未总结文章
  - 批量总结已选文章

- `/articles/[id]`
  - 查看正文与摘要
  - 查看来源信息
  - 执行或重跑 LLM 总结
  - 编辑文章标签

- `/reports`
  - 按日期生成日报
  - 按来源或来源分组缩小范围

- `/status`
  - 系统状态

## 技术结构

### 前端

- Next.js App Router
- 目录：`frontend/`

### 后端

- FastAPI
- 目录：`backend/`

### 基础设施

- PostgreSQL
- Redis
- Docker Compose

### QClaw

- 目录：`qclaw-skills/`
- 当前已打通：指定日期日报调用

## 推荐开发顺序

当前更合理的推进顺序是：

1. 继续打稳文章管理层
2. 完善来源管理与 taxonomy 使用体验
3. 建立 Notebook / 工作区机制
4. 基于 Notebook 做报告、博客、思维导图、播客脚本等生成
5. 再评估 MCP 与 QClaw + Codex CLI 调用链路

## 快速启动

### 试用环境

```powershell
git clone <repo>
cd FocusLedger
powershell -ExecutionPolicy Bypass -File .\scripts\quick-start.ps1
```

打开：

- 前端：[http://localhost:3000](http://localhost:3000)
- 后端健康检查：[http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

停止：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\quick-stop.ps1
```

### 开发环境

建议安装：

- Python 3.12
- Node.js 22
- Docker Desktop

复制环境变量：

```powershell
copy .env.example .env
```

启动 PostgreSQL 与 Redis：

```powershell
docker compose up -d postgres redis
```

启动后端：

```powershell
cd backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

启动前端：

```powershell
cd frontend
npm install
npm run dev
```

如果 `3000` 端口不可用：

```powershell
npm run dev:3300
```

## 关键目录

- `backend/src/api/`
- `backend/src/services/`
- `backend/src/integrations/wechat_ingestion/`
- `backend/src/llm/`
- `frontend/app/`
- `frontend/lib/`
- `docs/taxonomies/`
- `qclaw-skills/`
- `scripts/`

## Git 建议

建议纳入 Git：

- 前后端代码
- README
- AGENTS.md
- 数据库迁移文件
- taxonomy 文档
- 产品文档
- QClaw 技能定义
- 启动脚本

不应纳入 Git：

- `.env`
- 本地日志
- 本地缓存
- 临时导出文件
- `_ref_Access_wechat_article/`
- `.claude/`

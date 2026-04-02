# FocusLedger 项目说明

## 1. 项目定位

FocusLedger 是一个面向中文微信公众号文章的本地研究与内容整理工具。

当前正式目标：

1. 管理公众号来源并同步文章到本地文章库
2. 基于文章内容、来源分组和来源标签生成日报
3. 支持通过 QClaw 在微信中调用日报
4. 逐步演进为一个基于微信公众号文章的 NotebookLM 型产品

当前产品重心已经从“自动刷新凭据”转向“利用已有公众号文章数据做知识管理、专题研究和 AI 辅助整理”。

## 2. 当前正式实现边界

### 2.1 当前保留的同步能力

- 来源创建
- 公众号主页链接解析
- `profile_ext` 凭据保存
- 凭据状态检测
- 凭据手动更新
- 后台同步任务
- 文章去重与正文入库

### 2.2 当前不再作为主流程的能力

以下能力已经退出正式主链路：

- 自动启动 Fiddler
- 自动读取抓包结果
- 自动刷新凭据
- Fiddler callback / capture 流程

当前正式流程是：

1. 用户发起同步
2. 系统先验证凭据
3. 凭据有效则继续同步
4. 凭据失效则明确失败并提示手动更新
5. 用户在 `/collect` 页面粘贴新的 `profile_ext` 链接
6. 再重新发起同步

## 3. 当前产品方向

当前阶段 FocusLedger 更接近：

**一个基于微信公众号文章数据的本地知识库、工作区和 AI 辅助整理系统**

重点方向包括：

- 收藏管理
- 标签管理
- 工作区 / Notebook
- 基于工作区的问答与内容生成
- QClaw 触发与结果回传
- 后续通过 MCP 暴露 FocusLedger 能力

方向文档：

- `PRODUCT_NOTEBOOKLM_DIRECTION.md`

## 4. 阶段 A 当前重点

当前阶段 A 的目标是打稳文章管理层。

已经开始落地的能力：

- 把 LLM 总结从抓取流程中拆出来
- 文章独立的 LLM 总结状态
- 文章收藏状态
- 文章标签手动编辑
- 单篇文章 LLM 总结
- 按选中文章批量总结
- 按筛选条件批量总结未总结文章
- 文章标签分层筛选
- 来源 AI 分组与来源 AI 打标签

## 5. taxonomy 文档

当前维护的本地 taxonomy 文档：

- `docs/taxonomies/source-group-taxonomy.md`
- `docs/taxonomies/source-tag-taxonomy.md`
- `docs/taxonomies/article-tag-taxonomy.md`

这些文档用于：

- 约束公众号来源分组
- 约束公众号来源标签
- 约束文章主题标签与内容类型

设计原则：

- 分组只承担主归属
- 标签承担横向切片
- 文章标签支持多级路径
- 选择父标签时应命中子标签
- taxonomy 由 LLM 与人工共用

后续来源 AI 分组打标、文章 AI 打标签以及 MCP 调用都会基于这套文档继续推进。

## 6. 当前技术结构

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
  - 独立的 LLM 总结与标签
  - 来源 AI 分组与打标签
  - 日报生成
  - QClaw 接口

### 基础设施

- PostgreSQL
- Redis
- Docker Compose

### QClaw

- 目录：`qclaw-skills/`
- 当前已打通：指定日期日报调用

## 7. 当前正式产品边界

### 7.1 凭据不是永久有效

来源创建成功不代表后续永远可用。  
同步前必须显式验证凭据，凭据失效时必须明确返回失败和提示，不能误报成功。

### 7.2 当前同步链路允许人工参与

当前版本接受这样一个现实：

- 用户需要手动更新过期凭据
- 系统负责检测、提示、校验和继续同步

### 7.3 当前主价值不在“自动抓最新”

当前最值得投入的部分是：

- 已有文章数据的组织
- 文章库管理
- 工作区构建
- AI 助理交互

## 8. 已放弃或降级的技术路径

这些路径不再作为主线投入：

- mitmproxy
- 自研 Windows helper（`.NET 8 + Titanium.Web.Proxy`）
- FiddlerCore
- Fiddler Classic 半自动刷新主流程

## 9. 当前协作重点

开发时优先保护以下能力：

- 文章同步主链路
- 手动更新凭据主链路
- 文章独立 LLM 总结主链路
- 来源 AI 分组与打标签能力
- taxonomy 文档读取与约束链路

如果改动影响上述任一能力，合并前至少确认：

- 前端可启动
- 后端可启动
- `/articles`、`/sources`、`/collect` 可访问
- 当前正式同步链路未被破坏

## 10. 关键目录

- `backend/src/api/`
- `backend/src/services/`
- `backend/src/integrations/wechat_ingestion/`
- `backend/src/parsers/`
- `backend/src/llm/`
- `frontend/app/`
- `frontend/lib/`
- `docs/taxonomies/`
- `qclaw-skills/`
- `scripts/`

## 11. 协作与清理建议

### 建议纳入 Git

- 前端代码
- 后端代码
- README
- AGENTS.md
- 数据库迁移文件
- taxonomy 文档
- 产品文档
- QClaw 技能定义
- 启动脚本

### 不应纳入 Git

- `.env`
- 本地日志
- 本地缓存
- 临时导出文件
- `_ref_Access_wechat_article/`
- `.claude/`

## 12. 下一阶段开发重点

下一阶段优先级：

1. 继续完善文章数据库管理能力
2. 完善来源分组与来源标签管理体验
3. 设计工作区 / Notebook 机制
4. 设计基于工作区的报告、博客、思维导图、播客脚本生成
5. 明确可被 AI 调用的 FocusLedger 能力边界
6. 评估并设计 MCP 接口
7. 让 QClaw + Codex CLI + FocusLedger 形成最小闭环

当前不再把“自动刷新凭据”作为核心里程碑。

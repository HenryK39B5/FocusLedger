# FocusLedger 架构说明

## 总体结构

FocusLedger 采用前后端分离架构：

- `frontend/`：面向用户的中文 Web App
- `backend/`：负责采集、解析、存储、检索、推荐和反馈闭环

## 后端分层

- `src/api/`：HTTP 路由
- `src/core/`：配置、日志和基础设施
- `src/db/`：数据库连接与基础类
- `src/models/`：SQLAlchemy 数据模型
- `src/schemas/`：Pydantic 传输对象
- `src/services/`：业务服务层
- `src/ranking/`：推荐排序规则
- `src/novelty/`：增量识别逻辑
- `src/retrieval/`：相似内容召回
- `src/llm/`：可替换的 LLM 抽象
- `src/parsers/`：文章解析器
- `src/integrations/wechat_ingestion/`：微信公众号采集适配层
- `src/tasks/`：Celery 任务入口

## 数据流

1. 用户在前端添加公众号来源。
2. 后端将来源交给 `wechat_ingestion` 适配层。
3. 采集层抓取文章列表、正文 HTML 和互动数据。
4. 解析器抽取正文、标题、作者、发布时间、标签和结构化字段。
5. 文章与指标写入数据库，正文 HTML 落盘。
6. 推荐服务基于用户画像、文章新鲜度、主题匹配和增量信息排序。
7. 用户反馈回写，更新画像与后续推荐。

## 设计原则

- 保留可替换的采集入口，避免采集逻辑散落在业务层。
- LLM 抽象必须可替换，且没有 Key 时可继续运行规则退化路径。
- 相似召回、增量分析和推荐排序都保持可解释输出。


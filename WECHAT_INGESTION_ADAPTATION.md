# 微信采集适配说明

本项目参考了 `yeximm/Access_wechat_article` 的核心思路，并把它重构为 `backend/src/integrations/wechat_ingestion/` 子系统。

## 参考了哪些思路

- 基础抓取器负责单篇文章 HTML 获取和解析
- token / 参数解析单独封装
- 历史文章列表和文章详情分离处理
- 原始 HTML 落盘与结构化结果分离
- 顺序化采集流程集中编排
- 对微信 PC 端、Fiddler 抓包参数和 `mp.weixin.qq.com` 访问方式保持兼容思路

## 本项目做了哪些重构

- 从单体脚本改成 `frontend/` + `backend/` 分层架构
- 把抓取逻辑放进 `wechat_ingestion` 命名空间，而不是散落在入口文件
- 把 Excel 输出改成数据库持久化和 API 输出
- 把 HTML 保存能力和解析能力解耦
- 把推荐、增量识别和画像更新放到独立服务层

## 保留的关键流程

- 文章主页或 token 链接输入
- 文章列表获取
- 单篇文章正文抓取
- 互动数据抓取
- 原始 HTML 归档
- 结构化解析入库

## 为本项目封装了什么

- 统一的 `WeChatTokenLink` 解析器
- 统一的文章 HTML 解析器
- 可插拔的 `LLMProvider`
- 可替换的推荐评分器
- 可复用的相似文章召回逻辑

## 运行方式

- 本地开发时优先通过 `backend/src/integrations/wechat_ingestion/adapter/client.py` 进入采集流程
- 如果只想验证解析链路，可以直接调用 `pipeline/orchestrator.py`
- 如果没有可用的 LLM Key，系统会退化到规则分析，但仍会输出结构化结果


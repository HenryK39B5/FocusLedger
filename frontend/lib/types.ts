export type ArticleSource = {
  id: string;
  name: string;
  source_type: string;
  source_identifier: string;
  source_group?: string | null;
  tags: string[];
  description?: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type ArticleSourceDeleteResult = {
  source_id: string;
  source_name: string;
  deleted_article_count: number;
};

export type ArticleMetric = {
  read_count?: number | null;
  like_count?: number | null;
  repost_count?: number | null;
  comment_count?: number | null;
  comment_like_count?: number | null;
  captured_at: string;
};

export type ArticleSummary = {
  id: string;
  source_id: string;
  title: string;
  source_name: string;
  publish_time?: string | null;
  created_at: string;
  summary?: string | null;
  topic_tags: string[];
  style_tags: string[];
  source_tags: string[];
  source_group?: string | null;
};

export type Article = {
  id: string;
  source_id: string;
  title: string;
  author?: string | null;
  publish_time?: string | null;
  url: string;
  raw_html_path?: string | null;
  raw_text?: string | null;
  summary?: string | null;
  topic_tags: string[];
  entity_tags: string[];
  content_type?: string | null;
  core_claims: string[];
  key_variables: string[];
  catalysts: string[];
  risks: string[];
  style_tags: string[];
  metadata_json: Record<string, unknown>;
  source?: ArticleSource | null;
  metrics: ArticleMetric[];
  created_at: string;
  updated_at: string;
};

export type ArticleList = {
  items: ArticleSummary[];
  total: number;
  page: number;
  page_size: number;
};

export type DailyReportSection = {
  title: string;
  summary?: string | null;
  bullets: string[];
  article_ids: string[];
};

export type DailyReportArticle = {
  id: string;
  title: string;
  source_name: string;
  source_group?: string | null;
  source_tags: string[];
  publish_time?: string | null;
  summary?: string | null;
  topic_tags: string[];
  entity_tags: string[];
  style_tags: string[];
  content_type?: string | null;
  importance_score: number;
};

export type DailyReport = {
  date: string;
  title: string;
  overview?: string | null;
  report_markdown: string;
  follow_ups: string[];
  sections: DailyReportSection[];
  articles: DailyReportArticle[];
  stats: Record<string, unknown>;
  generated_at: string;
  source_id?: string | null;
  source_group?: string | null;
};

export type IngestionResult = {
  source_id: string;
  source_name: string;
  imported_count: number;
  updated_count: number;
  failed_count: number;
  message: string;
  article_ids: string[];
};

export type ArticleDeleteResult = {
  article_id: string;
  title: string;
};

export type ArticleBatchDeleteResult = {
  deleted_count: number;
  deleted_ids: string[];
};

export type WechatHomeLinkResolveResult = {
  article_url: string;
  article_title?: string | null;
  source_name?: string | null;
  biz?: string | null;
  public_home_link?: string | null;
  resolved: boolean;
  message?: string | null;
};

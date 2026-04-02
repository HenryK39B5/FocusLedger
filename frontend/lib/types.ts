export type SourceCredential = {
  id: string;
  source_id: string;
  provider: string;
  raw_link: string;
  token_biz: string;
  uin: string;
  appmsg_token?: string | null;
  session_us?: string | null;
  scene?: string | null;
  username?: string | null;
  created_at: string;
  updated_at: string;
};

export type ArticleSource = {
  id: string;
  name: string;
  source_type: string;
  biz: string;
  public_home_link: string;
  source_group?: string | null;
  tags: string[];
  description?: string | null;
  enabled: boolean;
  credential_status: string;
  last_verified_at?: string | null;
  last_sync_succeeded_at?: string | null;
  last_sync_failed_at?: string | null;
  last_error_code?: string | null;
  last_error_message?: string | null;
  credential?: SourceCredential | null;
  created_at: string;
  updated_at: string;
};

export type ArticleSourceDeleteResult = {
  source_id: string;
  source_name: string;
  deleted_article_count: number;
};

export type SourceBatchAnalyzeResult = {
  analyzed_count: number;
  analyzed_ids: string[];
  failed_ids: string[];
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
  tags: string[];
  all_tags: string[];
  topic_tags: string[];
  style_tags: string[];
  source_tags: string[];
  source_group?: string | null;
  content_type?: string | null;
  is_favorited: boolean;
  llm_summary_status: string;
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
  tags: string[];
  all_tags: string[];
  topic_tags: string[];
  entity_tags: string[];
  content_type?: string | null;
  core_claims: string[];
  key_variables: string[];
  catalysts: string[];
  risks: string[];
  style_tags: string[];
  metadata_json: Record<string, unknown>;
  is_favorited: boolean;
  llm_summary_status: string;
  llm_summary_updated_at?: string | null;
  llm_summary_error?: string | null;
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
  needs_refresh: boolean;
  credential_status_after_run: string;
  failure_reason_category?: string | null;
};

export type IngestionJob = {
  id: string;
  source_id: string;
  source_name: string;
  status: string;
  page_start: number;
  page_end: number;
  since_days?: number | null;
  current_stage?: string | null;
  current_article_title?: string | null;
  current_article_url?: string | null;
  processed_count: number;
  imported_count: number;
  updated_count: number;
  failed_count: number;
  total_candidates?: number | null;
  message?: string | null;
  failure_reason_category?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type IngestionJobList = {
  items: IngestionJob[];
};

export type SourceCredentialCheckResult = {
  source_id: string;
  source_name: string;
  valid: boolean;
  credential_status: string;
  needs_refresh: boolean;
  error_code?: string | null;
  error_message?: string | null;
  last_verified_at?: string | null;
  message: string;
};

export type ArticleDeleteResult = {
  article_id: string;
  title: string;
};

export type ArticleBatchDeleteResult = {
  deleted_count: number;
  deleted_ids: string[];
};

export type ArticleBatchAnalyzeResult = {
  analyzed_count: number;
  analyzed_ids: string[];
  failed_ids: string[];
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

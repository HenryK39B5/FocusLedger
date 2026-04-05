import type {
  Article,
  ArticleBatchAnalyzeResult,
  ArticleBatchDeleteResult,
  ArticleDeleteResult,
  ArticleList,
  ArticleSource,
  ArticleSourceDeleteResult,
  IngestionJob,
  IngestionJobList,
  IngestionResult,
  Notebook,
  NotebookChat,
  NotebookChatResponse,
  NotebookDeleteResult,
  NotebookList,
  NotebookPodcastAudioJob,
  NotebookPodcastScript,
  NotebookPodcastScriptDeleteResult,
  NotebookPodcastScriptList,
  SourceBatchAnalyzeResult,
  SourceCredentialCheckResult,
  WechatHomeLinkResolveResult,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = "";
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ? `：${payload.detail}` : "";
    } catch {
      detail = "";
    }
    throw new Error(`请求失败 ${response.status}${detail}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => apiFetch<{ status: string }>("/api/v1/health"),
  articles: (options?: {
    limit?: number;
    sourceId?: string;
    q?: string;
    page?: number;
    pageSize?: number;
    sort?: string;
    dateFrom?: string;
    dateTo?: string;
    llmStatus?: string;
    favoritedOnly?: boolean;
    tags?: string[];
  }) => {
    const params = new URLSearchParams();
    params.set("limit", String(options?.limit ?? 20));
    if (options?.sourceId) params.set("source_id", options.sourceId);
    if (options?.q) params.set("q", options.q);
    if (options?.page != null) params.set("page", String(options.page));
    if (options?.pageSize != null) params.set("page_size", String(options.pageSize));
    if (options?.sort) params.set("sort", options.sort);
    if (options?.dateFrom) params.set("date_from", options.dateFrom);
    if (options?.dateTo) params.set("date_to", options.dateTo);
    if (options?.llmStatus) params.set("llm_status", options.llmStatus);
    if (options?.favoritedOnly) params.set("favorited_only", "true");
    if (options?.tags?.length) params.set("tags", options.tags.join(","));
    return apiFetch<ArticleList>(`/api/v1/articles?${params.toString()}`);
  },
  article: (id: string) => apiFetch<Article>(`/api/v1/articles/${id}`),
  notebooks: () => apiFetch<NotebookList>("/api/v1/notebooks"),
  notebook: (id: string) => apiFetch<Notebook>(`/api/v1/notebooks/${id}`),
  notebookChat: (id: string) => apiFetch<NotebookChat>(`/api/v1/notebooks/${id}/chat`),
  notebookPodcasts: (id: string) => apiFetch<NotebookPodcastScriptList>(`/api/v1/notebooks/${id}/podcasts`),
  notebookPodcast: (notebookId: string, scriptId: string) =>
    apiFetch<NotebookPodcastScript>(`/api/v1/notebooks/${notebookId}/podcasts/${scriptId}`),
  notebookPodcastAudio: (notebookId: string, scriptId: string) =>
    apiFetch<NotebookPodcastAudioJob>(`/api/v1/notebooks/${notebookId}/podcasts/${scriptId}/audio`),
  createNotebook: (payload: { name: string; emoji?: string; description?: string | null }) =>
    apiFetch<Notebook>("/api/v1/notebooks", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateNotebook: (id: string, payload: { name?: string; emoji?: string; description?: string | null }) =>
    apiFetch<Notebook>(`/api/v1/notebooks/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteNotebook: (id: string) =>
    apiFetch<NotebookDeleteResult>(`/api/v1/notebooks/${id}`, {
      method: "DELETE",
    }),
  addNotebookArticles: (id: string, articleIds: string[]) =>
    apiFetch<Notebook>(`/api/v1/notebooks/${id}/articles`, {
      method: "POST",
      body: JSON.stringify({ article_ids: articleIds }),
    }),
  removeNotebookArticle: (id: string, articleId: string) =>
    apiFetch<Notebook>(`/api/v1/notebooks/${id}/articles/${articleId}`, {
      method: "DELETE",
    }),
  askNotebookChat: (id: string, message: string) =>
    apiFetch<NotebookChatResponse>(`/api/v1/notebooks/${id}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  clearNotebookChat: (id: string) =>
    apiFetch<NotebookChat>(`/api/v1/notebooks/${id}/chat`, {
      method: "DELETE",
    }),
  generateNotebookPodcast: (
    id: string,
    payload: { format: string; targetMinutes: number; focusPrompt?: string; articleIds?: string[] },
  ) =>
    apiFetch<NotebookPodcastScript>(`/api/v1/notebooks/${id}/podcasts`, {
      method: "POST",
      body: JSON.stringify({
        format: payload.format,
        target_minutes: payload.targetMinutes,
        focus_prompt: payload.focusPrompt ?? null,
        article_ids: payload.articleIds ?? [],
      }),
    }),
  deleteNotebookPodcast: (notebookId: string, scriptId: string) =>
    apiFetch<NotebookPodcastScriptDeleteResult>(`/api/v1/notebooks/${notebookId}/podcasts/${scriptId}`, {
      method: "DELETE",
    }),
  createNotebookPodcastAudio: (
    notebookId: string,
    scriptId: string,
    options?: {
      engine?: "edge" | "tencent";
      voice?: string;
      voiceMode?: "female" | "male" | "duet";
      rate?: string;
    },
  ) =>
    apiFetch<NotebookPodcastAudioJob>(`/api/v1/notebooks/${notebookId}/podcasts/${scriptId}/audio`, {
      method: "POST",
      body: JSON.stringify({
        engine: options?.engine ?? "edge",
        voice: options?.voice ?? "zh-CN-XiaoxiaoNeural",
        voice_mode: options?.voiceMode ?? null,
        rate: options?.rate ?? "-8%",
      }),
    }),
  updateArticle: (id: string, payload: { tags?: string[]; is_favorited?: boolean }) =>
    apiFetch<Article>(`/api/v1/articles/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  analyzeArticle: (id: string) =>
    apiFetch<Article>(`/api/v1/articles/${id}/analyze`, {
      method: "POST",
    }),
  deleteArticle: (id: string) =>
    apiFetch<ArticleDeleteResult>(`/api/v1/articles/${id}`, {
      method: "DELETE",
    }),
  batchDeleteArticles: (articleIds: string[]) =>
    apiFetch<ArticleBatchDeleteResult>("/api/v1/articles/batch-delete", {
      method: "POST",
      body: JSON.stringify({ article_ids: articleIds }),
    }),
  batchAnalyzeArticles: (articleIds: string[]) =>
    apiFetch<ArticleBatchAnalyzeResult>("/api/v1/articles/batch-analyze", {
      method: "POST",
      body: JSON.stringify({ article_ids: articleIds }),
    }),
  batchAnalyzeArticlesByQuery: (payload: {
    sourceId?: string;
    q?: string;
    dateFrom?: string;
    dateTo?: string;
    favoritedOnly?: boolean;
    tags?: string[];
    maxItems?: number;
    target?: string;
  }) =>
    apiFetch<ArticleBatchAnalyzeResult>("/api/v1/articles/batch-analyze-query", {
      method: "POST",
      body: JSON.stringify({
        source_id: payload.sourceId ?? null,
        q: payload.q ?? null,
        date_from: payload.dateFrom ?? null,
        date_to: payload.dateTo ?? null,
        favorited_only: payload.favoritedOnly ?? false,
        tags: payload.tags ?? [],
        max_items: payload.maxItems ?? 100,
        target: payload.target ?? "pending",
      }),
    }),
  sources: () => apiFetch<ArticleSource[]>("/api/v1/sources"),
  createSource: (payload: Record<string, unknown>) =>
    apiFetch<ArticleSource>("/api/v1/sources", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  resolveWechatHome: (articleUrl: string) =>
    apiFetch<WechatHomeLinkResolveResult>("/api/v1/wechat/resolve-home", {
      method: "POST",
      body: JSON.stringify({ article_url: articleUrl }),
    }),
  updateSource: (sourceId: string, payload: Record<string, unknown>) =>
    apiFetch<ArticleSource>(`/api/v1/sources/${sourceId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  analyzeSource: (sourceId: string) =>
    apiFetch<ArticleSource>(`/api/v1/sources/${sourceId}/analyze`, {
      method: "POST",
    }),
  batchAnalyzeSources: (sourceIds: string[]) =>
    apiFetch<SourceBatchAnalyzeResult>("/api/v1/sources/batch-analyze", {
      method: "POST",
      body: JSON.stringify({ source_ids: sourceIds }),
    }),
  updateSourceCredential: (sourceId: string, payload: { raw_link: string; validate_after_update?: boolean }) =>
    apiFetch<ArticleSource>(`/api/v1/sources/${sourceId}/credential`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  verifySourceCredential: (sourceId: string) =>
    apiFetch<SourceCredentialCheckResult>(`/api/v1/sources/${sourceId}/credential/verify`, {
      method: "POST",
    }),
  deleteSource: (sourceId: string) =>
    apiFetch<ArticleSourceDeleteResult>(`/api/v1/sources/${sourceId}`, {
      method: "DELETE",
    }),
  runIngestion: (sourceId: string, options?: { pageStart?: number; pageEnd?: number; sinceDays?: number | null }) => {
    const params = new URLSearchParams();
    if (options?.pageStart != null) params.set("page_start", String(options.pageStart));
    if (options?.pageEnd != null) params.set("page_end", String(options.pageEnd));
    if (options?.sinceDays != null) params.set("since_days", String(options.sinceDays));
    const query = params.toString();
    return apiFetch<IngestionResult>(`/api/v1/ingestions/${sourceId}/run${query ? `?${query}` : ""}`, {
      method: "POST",
    });
  },
  createIngestionJob: (payload: {
    sourceId: string;
    pageStart?: number;
    pageEnd?: number;
    sinceDays?: number | null;
    dateFrom?: string | null;
    dateTo?: string | null;
  }) =>
    apiFetch<IngestionJob>("/api/v1/ingestion-jobs", {
      method: "POST",
      body: JSON.stringify({
        source_id: payload.sourceId,
        page_start: payload.pageStart ?? 1,
        page_end: payload.pageEnd ?? 20,
        since_days: payload.sinceDays ?? null,
        date_from: payload.dateFrom ?? null,
        date_to: payload.dateTo ?? null,
      }),
    }),
  ingestionJobs: (options?: { sourceId?: string; limit?: number }) => {
    const params = new URLSearchParams();
    if (options?.sourceId) params.set("source_id", options.sourceId);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return apiFetch<IngestionJobList>(`/api/v1/ingestion-jobs${params.toString() ? `?${params.toString()}` : ""}`);
  },
  ingestionJob: (jobId: string) => apiFetch<IngestionJob>(`/api/v1/ingestion-jobs/${jobId}`),
  status: () => apiFetch<Record<string, unknown>>("/api/v1/system/status"),
  articleTagTaxonomy: () => apiFetch<{ tags: string[] }>("/api/v1/system/taxonomies/article-tags"),
};

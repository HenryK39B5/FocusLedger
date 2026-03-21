import type {
  Article,
  ArticleBatchDeleteResult,
  ArticleDeleteResult,
  ArticleList,
  ArticleSource,
  ArticleSourceDeleteResult,
  DailyReport,
  IngestionResult,
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
    throw new Error(`请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => apiFetch<{ status: string }>("/api/v1/health"),
  dailyReport: (options?: { date?: string; sourceId?: string; sourceGroup?: string; limit?: number }) => {
    const params = new URLSearchParams();
    if (options?.date) {
      params.set("date", options.date);
    }
    if (options?.sourceId) {
      params.set("source_id", options.sourceId);
    }
    if (options?.sourceGroup) {
      params.set("source_group", options.sourceGroup);
    }
    if (options?.limit != null) {
      params.set("limit", String(options.limit));
    }
    return apiFetch<DailyReport>(`/api/v1/reports/daily${params.toString() ? `?${params.toString()}` : ""}`);
  },
  articles: (options?: {
    limit?: number;
    sourceId?: string;
    q?: string;
    page?: number;
    pageSize?: number;
    sort?: string;
    dateFrom?: string;
    dateTo?: string;
  }) => {
    const params = new URLSearchParams();
    params.set("limit", String(options?.limit ?? 20));
    if (options?.sourceId) {
      params.set("source_id", options.sourceId);
    }
    if (options?.q) {
      params.set("q", options.q);
    }
    if (options?.page != null) {
      params.set("page", String(options.page));
    }
    if (options?.pageSize != null) {
      params.set("page_size", String(options.pageSize));
    }
    if (options?.sort) {
      params.set("sort", options.sort);
    }
    if (options?.dateFrom) {
      params.set("date_from", options.dateFrom);
    }
    if (options?.dateTo) {
      params.set("date_to", options.dateTo);
    }
    return apiFetch<ArticleList>(`/api/v1/articles?${params.toString()}`);
  },
  article: (id: string) => apiFetch<Article>(`/api/v1/articles/${id}`),
  deleteArticle: (id: string) =>
    apiFetch<ArticleDeleteResult>(`/api/v1/articles/${id}`, {
      method: "DELETE",
    }),
  batchDeleteArticles: (articleIds: string[]) =>
    apiFetch<ArticleBatchDeleteResult>("/api/v1/articles/batch-delete", {
      method: "POST",
      body: JSON.stringify({ article_ids: articleIds }),
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
  deleteSource: (sourceId: string) =>
    apiFetch<ArticleSourceDeleteResult>(`/api/v1/sources/${sourceId}`, {
      method: "DELETE",
    }),
  runIngestion: (sourceId: string, options?: { pageStart?: number; pageEnd?: number; sinceDays?: number | null }) => {
    const params = new URLSearchParams();
    if (options?.pageStart != null) {
      params.set("page_start", String(options.pageStart));
    }
    if (options?.pageEnd != null) {
      params.set("page_end", String(options.pageEnd));
    }
    if (options?.sinceDays != null) {
      params.set("since_days", String(options.sinceDays));
    }
    const query = params.toString();
    return apiFetch<IngestionResult>(`/api/v1/ingestions/${sourceId}/run${query ? `?${query}` : ""}`, {
      method: "POST",
    });
  },
  status: () => apiFetch<Record<string, unknown>>("/api/v1/system/status"),
};

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useDailyReport(options?: {
  date?: string;
  sourceId?: string;
  sourceGroup?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: [
      "daily-report",
      options?.date ?? "",
      options?.sourceId ?? "all",
      options?.sourceGroup ?? "all",
      options?.limit ?? 20,
    ],
    queryFn: () =>
      api.dailyReport({
        date: options?.date,
        sourceId: options?.sourceId,
        sourceGroup: options?.sourceGroup,
        limit: options?.limit ?? 20,
      }),
    enabled: Boolean(options?.date),
  });
}

export function useSources() {
  return useQuery({
    queryKey: ["sources"],
    queryFn: () => api.sources(),
  });
}

export function useIngestionJobs(options?: { sourceId?: string; limit?: number; refetchInterval?: number | false }) {
  return useQuery({
    queryKey: ["ingestion-jobs", options?.sourceId ?? "all", options?.limit ?? 50],
    queryFn: () => api.ingestionJobs({ sourceId: options?.sourceId, limit: options?.limit ?? 50 }),
    refetchInterval: options?.refetchInterval ?? false,
  });
}

export function useIngestionJob(jobId: string | null, options?: { refetchInterval?: number | false }) {
  return useQuery({
    queryKey: ["ingestion-job", jobId ?? ""],
    queryFn: () => api.ingestionJob(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: options?.refetchInterval ?? false,
  });
}

export function useArticle(articleId: string) {
  return useQuery({
    queryKey: ["article", articleId],
    queryFn: () => api.article(articleId),
    enabled: Boolean(articleId),
  });
}

export function useArticles(options?: {
  sourceId?: string;
  q?: string;
  page?: number;
  pageSize?: number;
  sort?: string;
  dateFrom?: string;
  dateTo?: string;
}) {
  return useQuery({
    queryKey: [
      "articles",
      options?.sourceId ?? "all",
      options?.q ?? "",
      options?.page ?? 1,
      options?.pageSize ?? 24,
      options?.sort ?? "latest",
      options?.dateFrom ?? "",
      options?.dateTo ?? "",
    ],
    queryFn: () =>
      api.articles({
        limit: options?.pageSize ?? 24,
        sourceId: options?.sourceId,
        q: options?.q,
        page: options?.page ?? 1,
        pageSize: options?.pageSize ?? 24,
        sort: options?.sort ?? "latest",
        dateFrom: options?.dateFrom,
        dateTo: options?.dateTo,
      }),
  });
}

export function useStatus() {
  return useQuery({
    queryKey: ["status"],
    queryFn: () => api.status(),
  });
}

export function useMutations() {
  const queryClient = useQueryClient();

  return {
    createSource: useMutation({
      mutationFn: api.createSource,
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
      },
    }),
    updateSource: useMutation({
      mutationFn: ({ sourceId, payload }: { sourceId: string; payload: Record<string, unknown> }) =>
        api.updateSource(sourceId, payload),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
      },
    }),
    updateSourceCredential: useMutation({
      mutationFn: ({ sourceId, rawLink, validateAfterUpdate = true }: { sourceId: string; rawLink: string; validateAfterUpdate?: boolean }) =>
        api.updateSourceCredential(sourceId, {
          raw_link: rawLink,
          validate_after_update: validateAfterUpdate,
        }),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
      },
    }),
    verifySourceCredential: useMutation({
      mutationFn: (sourceId: string) => api.verifySourceCredential(sourceId),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
      },
    }),
    deleteSource: useMutation({
      mutationFn: (sourceId: string) => api.deleteSource(sourceId),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
        await queryClient.invalidateQueries({ queryKey: ["articles"] });
        await queryClient.invalidateQueries({ queryKey: ["daily-report"] });
      },
    }),
    deleteArticle: useMutation({
      mutationFn: (articleId: string) => api.deleteArticle(articleId),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["articles"] });
        await queryClient.invalidateQueries({ queryKey: ["daily-report"] });
      },
    }),
    batchDeleteArticles: useMutation({
      mutationFn: (articleIds: string[]) => api.batchDeleteArticles(articleIds),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["articles"] });
        await queryClient.invalidateQueries({ queryKey: ["daily-report"] });
      },
    }),
    runIngestion: useMutation({
      mutationFn: (payload: { sourceId: string; pageStart?: number; pageEnd?: number; sinceDays?: number | null }) =>
        api.runIngestion(payload.sourceId, {
          pageStart: payload.pageStart,
          pageEnd: payload.pageEnd,
          sinceDays: payload.sinceDays,
        }),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["articles"] });
        await queryClient.invalidateQueries({ queryKey: ["daily-report"] });
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
      },
    }),
    createIngestionJob: useMutation({
      mutationFn: (payload: { sourceId: string; pageStart?: number; pageEnd?: number; sinceDays?: number | null }) =>
        api.createIngestionJob(payload),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["ingestion-jobs"] });
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
      },
    }),
    resolveWechatHome: useMutation({
      mutationFn: api.resolveWechatHome,
    }),
  };
}

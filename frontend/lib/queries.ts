import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

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
  llmStatus?: string;
  favoritedOnly?: boolean;
  tags?: string[];
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
      options?.llmStatus ?? "all",
      options?.favoritedOnly ? "favorited" : "all",
      (options?.tags ?? []).join("|"),
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
        llmStatus: options?.llmStatus,
        favoritedOnly: options?.favoritedOnly,
        tags: options?.tags,
      }),
  });
}

export function useNotebooks() {
  return useQuery({
    queryKey: ["notebooks"],
    queryFn: () => api.notebooks(),
  });
}

export function useNotebook(notebookId: string | null) {
  return useQuery({
    queryKey: ["notebook", notebookId ?? ""],
    queryFn: () => api.notebook(notebookId as string),
    enabled: Boolean(notebookId),
  });
}

export function useNotebookChat(notebookId: string | null) {
  return useQuery({
    queryKey: ["notebook-chat", notebookId ?? ""],
    queryFn: () => api.notebookChat(notebookId as string),
    enabled: Boolean(notebookId),
  });
}

export function useNotebookPodcasts(notebookId: string | null) {
  return useQuery({
    queryKey: ["notebook-podcasts", notebookId ?? ""],
    queryFn: () => api.notebookPodcasts(notebookId as string),
    enabled: Boolean(notebookId),
  });
}

export function useNotebookPodcastAudio(
  notebookId: string | null,
  scriptId: string | null,
  options?: { enabled?: boolean; refetchInterval?: number | false },
) {
  return useQuery({
    queryKey: ["notebook-podcast-audio", notebookId ?? "", scriptId ?? ""],
    queryFn: () => api.notebookPodcastAudio(notebookId as string, scriptId as string),
    enabled: Boolean(notebookId && scriptId && (options?.enabled ?? true)),
    refetchInterval: options?.refetchInterval ?? false,
  });
}

export function useStatus() {
  return useQuery({
    queryKey: ["status"],
    queryFn: () => api.status(),
  });
}

export function useArticleTagTaxonomy() {
  return useQuery({
    queryKey: ["article-tag-taxonomy"],
    queryFn: () => api.articleTagTaxonomy(),
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
    analyzeSource: useMutation({
      mutationFn: (sourceId: string) => api.analyzeSource(sourceId),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
      },
    }),
    batchAnalyzeSources: useMutation({
      mutationFn: (sourceIds: string[]) => api.batchAnalyzeSources(sourceIds),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
      },
    }),
    updateSourceCredential: useMutation({
      mutationFn: ({
        sourceId,
        rawLink,
        validateAfterUpdate = true,
      }: {
        sourceId: string;
        rawLink: string;
        validateAfterUpdate?: boolean;
      }) =>
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
      },
    }),
    deleteArticle: useMutation({
      mutationFn: (articleId: string) => api.deleteArticle(articleId),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["articles"] });
      },
    }),
    updateArticle: useMutation({
      mutationFn: ({
        articleId,
        payload,
      }: {
        articleId: string;
        payload: { tags?: string[]; is_favorited?: boolean };
      }) => api.updateArticle(articleId, payload),
      onSuccess: async (_data, variables) => {
        await queryClient.invalidateQueries({ queryKey: ["articles"] });
        await queryClient.invalidateQueries({ queryKey: ["article", variables.articleId] });
      },
    }),
    createNotebook: useMutation({
      mutationFn: (payload: { name: string; emoji?: string; description?: string | null }) => api.createNotebook(payload),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks"] });
      },
    }),
    updateNotebook: useMutation({
      mutationFn: ({
        notebookId,
        payload,
      }: {
        notebookId: string;
        payload: { name?: string; emoji?: string; description?: string | null };
      }) => api.updateNotebook(notebookId, payload),
      onSuccess: async (_data, variables) => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks"] });
        await queryClient.invalidateQueries({ queryKey: ["notebook", variables.notebookId] });
      },
    }),
    deleteNotebook: useMutation({
      mutationFn: (notebookId: string) => api.deleteNotebook(notebookId),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks"] });
      },
    }),
    addNotebookArticles: useMutation({
      mutationFn: ({ notebookId, articleIds }: { notebookId: string; articleIds: string[] }) =>
        api.addNotebookArticles(notebookId, articleIds),
      onSuccess: async (_data, variables) => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks"] });
        await queryClient.invalidateQueries({ queryKey: ["notebook", variables.notebookId] });
      },
    }),
    removeNotebookArticle: useMutation({
      mutationFn: ({ notebookId, articleId }: { notebookId: string; articleId: string }) =>
        api.removeNotebookArticle(notebookId, articleId),
      onSuccess: async (_data, variables) => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks"] });
        await queryClient.invalidateQueries({ queryKey: ["notebook", variables.notebookId] });
      },
    }),
    askNotebookChat: useMutation({
      mutationFn: ({ notebookId, message }: { notebookId: string; message: string }) =>
        api.askNotebookChat(notebookId, message),
      onSuccess: async (_data, variables) => {
        await queryClient.invalidateQueries({ queryKey: ["notebook-chat", variables.notebookId] });
      },
    }),
    clearNotebookChat: useMutation({
      mutationFn: (notebookId: string) => api.clearNotebookChat(notebookId),
      onSuccess: async (_data, notebookId) => {
        await queryClient.invalidateQueries({ queryKey: ["notebook-chat", notebookId] });
      },
    }),
    generateNotebookPodcast: useMutation({
      mutationFn: ({
        notebookId,
        payload,
      }: {
        notebookId: string;
        payload: { format: string; targetMinutes: number; focusPrompt?: string; articleIds?: string[] };
      }) => api.generateNotebookPodcast(notebookId, payload),
      onSuccess: async (_data, variables) => {
        await queryClient.invalidateQueries({ queryKey: ["notebook-podcasts", variables.notebookId] });
      },
    }),
    deleteNotebookPodcast: useMutation({
      mutationFn: ({ notebookId, scriptId }: { notebookId: string; scriptId: string }) =>
        api.deleteNotebookPodcast(notebookId, scriptId),
      onSuccess: async (_data, variables) => {
        await queryClient.invalidateQueries({ queryKey: ["notebook-podcasts", variables.notebookId] });
      },
    }),
    createNotebookPodcastAudio: useMutation({
      mutationFn: ({
        notebookId,
        scriptId,
        options,
      }: {
        notebookId: string;
        scriptId: string;
        options?: {
          engine?: "edge" | "tencent";
          voice?: string;
          voiceMode?: "female" | "male" | "duet";
          rate?: string;
        };
      }) => api.createNotebookPodcastAudio(notebookId, scriptId, options),
      onSuccess: async (_data, variables) => {
        await queryClient.invalidateQueries({ queryKey: ["notebook-podcasts", variables.notebookId] });
        await queryClient.invalidateQueries({
          queryKey: ["notebook-podcast-audio", variables.notebookId, variables.scriptId],
        });
      },
    }),
    analyzeArticle: useMutation({
      mutationFn: (articleId: string) => api.analyzeArticle(articleId),
      onSuccess: async (_data, articleId) => {
        await queryClient.invalidateQueries({ queryKey: ["articles"] });
        await queryClient.invalidateQueries({ queryKey: ["article", articleId] });
      },
    }),
    batchAnalyzeArticles: useMutation({
      mutationFn: (articleIds: string[]) => api.batchAnalyzeArticles(articleIds),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["articles"] });
      },
    }),
    batchAnalyzeArticlesByQuery: useMutation({
      mutationFn: (payload: {
        sourceId?: string;
        q?: string;
        dateFrom?: string;
        dateTo?: string;
        favoritedOnly?: boolean;
        tags?: string[];
        maxItems?: number;
        target?: string;
      }) => api.batchAnalyzeArticlesByQuery(payload),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["articles"] });
      },
    }),
    batchDeleteArticles: useMutation({
      mutationFn: (articleIds: string[]) => api.batchDeleteArticles(articleIds),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["articles"] });
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
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
      },
    }),
    createIngestionJob: useMutation({
      mutationFn: (payload: {
        sourceId: string;
        pageStart?: number;
        pageEnd?: number;
        sinceDays?: number | null;
        dateFrom?: string | null;
        dateTo?: string | null;
      }) => api.createIngestionJob(payload),
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

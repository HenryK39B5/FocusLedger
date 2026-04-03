"use client";

import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";
import { RefreshCw, Search, Sparkles, Star, Trash2, X } from "lucide-react";
import { useArticleTagTaxonomy, useArticles, useMutations, useSources } from "@/lib/queries";
import { ActionButton, EmptyState, Input, PageFrame, SectionTitle, TagPills } from "@/components/ui";

function llmStatusLabel(status: string) {
  switch (status) {
    case "completed":
      return "已总结";
    case "failed":
      return "总结失败";
    case "processing":
      return "总结中";
    default:
      return "未总结";
  }
}

function llmStatusTone(status: string) {
  switch (status) {
    case "completed":
      return "border-emerald-400/30 bg-emerald-500/10 text-emerald-100";
    case "failed":
      return "border-red-400/30 bg-red-500/10 text-red-100";
    case "processing":
      return "border-sky-400/30 bg-sky-500/10 text-sky-100";
    default:
      return "border-amber-400/30 bg-amber-500/10 text-amber-100";
  }
}

export default function ArticlesPage() {
  const sources = useSources();
  const taxonomy = useArticleTagTaxonomy();
  const mutations = useMutations();

  const [sourceId, setSourceId] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<"latest" | "oldest">("latest");
  const [pageSize, setPageSize] = useState(24);
  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [llmStatus, setLlmStatus] = useState("");
  const [favoritedOnly, setFavoritedOnly] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [tagQuery, setTagQuery] = useState("");
  const [tagPickerOpen, setTagPickerOpen] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const deferredQuery = useDeferredValue(query);
  const articles = useArticles({
    sourceId: sourceId || undefined,
    q: deferredQuery.trim() || undefined,
    page,
    pageSize,
    sort,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
    llmStatus: llmStatus || undefined,
    favoritedOnly,
    tags: selectedTags,
  });

  const currentItems = articles.data?.items ?? [];
  const total = articles.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const allCurrentPageSelected = currentItems.length > 0 && currentItems.every((item) => selectedIds.includes(item.id));
  const selectedCount = selectedIds.length;

  const taxonomyTags = taxonomy.data?.tags ?? [];
  const usedArticleTags = useMemo(() => {
    return Array.from(new Set(currentItems.flatMap((item) => item.tags ?? []))).sort((left, right) =>
      left.localeCompare(right, "zh-Hans-CN"),
    );
  }, [currentItems]);

  const availableTags = useMemo(() => {
    const merged = Array.from(new Set([...taxonomyTags, ...usedArticleTags]));
    return merged.sort((left, right) => left.localeCompare(right, "zh-Hans-CN"));
  }, [taxonomyTags, usedArticleTags]);

  const filteredTagOptions = useMemo(() => {
    const keyword = tagQuery.trim().toLowerCase();
    return availableTags.filter((tag) => {
      if (selectedTags.includes(tag)) {
        return false;
      }
      if (!keyword) {
        return true;
      }
      return tag.toLowerCase().includes(keyword);
    });
  }, [availableTags, selectedTags, tagQuery]);

  function resetPage() {
    setPage(1);
    setSelectedIds([]);
  }

  function toggleArticle(articleId: string) {
    setSelectedIds((current) =>
      current.includes(articleId) ? current.filter((item) => item !== articleId) : [...current, articleId],
    );
  }

  function toggleSelectCurrentPage() {
    const currentIds = currentItems.map((item) => item.id);
    if (allCurrentPageSelected) {
      setSelectedIds((current) => current.filter((id) => !currentIds.includes(id)));
      return;
    }
    setSelectedIds((current) => Array.from(new Set([...current, ...currentIds])));
  }

  function addTag(tag: string) {
    setSelectedTags((current) => (current.includes(tag) ? current : [...current, tag]));
    setTagQuery("");
    setTagPickerOpen(true);
    resetPage();
  }

  function removeTag(tag: string) {
    setSelectedTags((current) => current.filter((item) => item !== tag));
    resetPage();
  }

  async function handleDeleteOne(articleId: string, title: string) {
    if (!window.confirm(`确认删除文章《${title}》吗？`)) {
      return;
    }
    await mutations.deleteArticle.mutateAsync(articleId);
    setSelectedIds((current) => current.filter((id) => id !== articleId));
  }

  async function handleBatchDelete() {
    if (!selectedIds.length) {
      return;
    }
    if (!window.confirm(`确认批量删除已选中的 ${selectedIds.length} 篇文章吗？`)) {
      return;
    }
    await mutations.batchDeleteArticles.mutateAsync(selectedIds);
    setSelectedIds([]);
    setActionMessage(`已删除 ${selectedCount} 篇文章。`);
  }

  async function handleBatchAnalyzeSelected() {
    if (!selectedIds.length) {
      return;
    }
    const result = await mutations.batchAnalyzeArticles.mutateAsync(selectedIds);
    setSelectedIds([]);
    setActionMessage(
      result.failed_ids.length
        ? `已完成 ${result.analyzed_count} 篇，另有 ${result.failed_ids.length} 篇总结失败。`
        : `已完成 ${result.analyzed_count} 篇已选文章的 LLM 总结。`,
    );
  }

  async function handleBatchAnalyzeByQuery() {
    const result = await mutations.batchAnalyzeArticlesByQuery.mutateAsync({
      sourceId: sourceId || undefined,
      q: deferredQuery.trim() || undefined,
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
      favoritedOnly,
      tags: selectedTags,
      maxItems: Math.max(total, 1),
      target: "pending",
    });
    setSelectedIds([]);
    setActionMessage(
      result.failed_ids.length
        ? `已完成 ${result.analyzed_count} 篇，另有 ${result.failed_ids.length} 篇总结失败。`
        : result.analyzed_count
          ? `已为当前筛选结果中的 ${result.analyzed_count} 篇未总结文章执行 LLM 总结。`
          : "当前筛选结果中没有未总结文章。",
    );
  }

  return (
    <PageFrame
      title="文章浏览"
      subtitle="搜索、筛选、收藏与批量整理文章库。"
      actions={
        <ActionButton variant="ghost" onClick={() => articles.refetch()}>
          <RefreshCw size={14} className="mr-2" />
          刷新
        </ActionButton>
      }
    >
      {actionMessage ? (
        <div className="mb-5 rounded-[20px] border border-[#ffd478]/22 bg-[#ffd478]/10 px-4 py-3 text-sm text-[#ffe7b8]">
          {actionMessage}
        </div>
      ) : null}
      <section className="rounded-[26px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.03))] p-4 shadow-glow">
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(360px,0.95fr)]">
          <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
            <div className="flex items-center gap-3 text-white/45">
              <Search size={16} />
              <p className="text-xs uppercase tracking-[0.28em]">Search</p>
            </div>
            <div className="mt-4 flex flex-col gap-3 lg:flex-row">
              <Input
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  resetPage();
                }}
                placeholder="搜索标题、摘要、正文或来源名称"
                className="h-11 flex-1 rounded-[18px] bg-white/6"
              />
              <ActionButton variant="ghost" onClick={() => articles.refetch()} className="h-11 px-5">
                搜索
              </ActionButton>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-[18px] border border-white/10 bg-white/5 p-3.5">
                <label className="mb-2 block text-xs uppercase tracking-[0.24em] text-white/42">来源</label>
                <select
                  value={sourceId}
                  onChange={(event) => {
                    setSourceId(event.target.value);
                    resetPage();
                  }}
                  className="w-full rounded-[16px] border border-white/12 bg-white/5 px-3 py-2.5 text-[13px] text-white outline-none"
                >
                  <option value="">全部来源</option>
                  {(sources.data ?? []).map((source) => (
                    <option key={source.id} value={source.id}>
                      {source.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="rounded-[18px] border border-white/10 bg-white/5 p-3.5">
                <label className="mb-2 block text-xs uppercase tracking-[0.24em] text-white/42">总结状态</label>
                <select
                  value={llmStatus}
                  onChange={(event) => {
                    setLlmStatus(event.target.value);
                    resetPage();
                  }}
                  className="w-full rounded-[16px] border border-white/12 bg-white/5 px-3 py-2.5 text-[13px] text-white outline-none"
                >
                  <option value="">全部状态</option>
                  <option value="pending">未总结</option>
                  <option value="completed">已总结</option>
                  <option value="failed">总结失败</option>
                  <option value="processing">总结中</option>
                </select>
              </div>
              <div className="rounded-[18px] border border-white/10 bg-white/5 p-3.5">
                <label className="mb-2 block text-xs uppercase tracking-[0.24em] text-white/42">排序</label>
                <select
                  value={sort}
                  onChange={(event) => {
                    setSort(event.target.value as "latest" | "oldest");
                    resetPage();
                  }}
                  className="w-full rounded-[16px] border border-white/12 bg-white/5 px-3 py-2.5 text-[13px] text-white outline-none"
                >
                  <option value="latest">最新优先</option>
                  <option value="oldest">最早优先</option>
                </select>
              </div>
              <div className="rounded-[18px] border border-white/10 bg-white/5 p-3.5">
                <label className="mb-2 block text-xs uppercase tracking-[0.24em] text-white/42">每页条数</label>
                <select
                  value={pageSize}
                  onChange={(event) => {
                    setPageSize(Number(event.target.value) || 24);
                    resetPage();
                  }}
                  className="w-full rounded-[16px] border border-white/12 bg-white/5 px-3 py-2.5 text-[13px] text-white outline-none"
                >
                  <option value={12}>12</option>
                  <option value={24}>24</option>
                  <option value={48}>48</option>
                  <option value={100}>100</option>
                </select>
              </div>
            </div>
          </div>

          <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-white/42">Refine</p>
                <h3 className="mt-2 text-lg font-semibold text-white">时间与收藏筛选</h3>
              </div>
              <label className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-3.5 py-2 text-[13px] text-white/75">
                <input
                  type="checkbox"
                  checked={favoritedOnly}
                  onChange={(event) => {
                    setFavoritedOnly(event.target.checked);
                    resetPage();
                  }}
                />
                只看收藏
              </label>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-[18px] border border-white/10 bg-white/5 p-3.5">
                <label className="mb-2 block text-xs uppercase tracking-[0.24em] text-white/42">起始日期</label>
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(event) => {
                    setDateFrom(event.target.value);
                    resetPage();
                  }}
                />
              </div>
              <div className="rounded-[18px] border border-white/10 bg-white/5 p-3.5">
                <label className="mb-2 block text-xs uppercase tracking-[0.24em] text-white/42">结束日期</label>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(event) => {
                    setDateTo(event.target.value);
                    resetPage();
                  }}
                />
              </div>
            </div>
            <div className="mt-5 rounded-[18px] border border-dashed border-white/10 bg-white/4 px-4 py-3 text-[13px] leading-6 text-white/52">
              当前结果共 {total} 篇文章。你可以直接整理全部未总结文章，也可以先勾选一部分再处理。
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <ActionButton
                variant="solid"
                onClick={handleBatchAnalyzeByQuery}
                disabled={mutations.batchAnalyzeArticlesByQuery.isPending || !total}
                className="h-11 justify-center"
              >
                <Sparkles size={14} className="mr-2" />
                {mutations.batchAnalyzeArticlesByQuery.isPending ? "批量总结中..." : "总结当前筛选下全部未总结文章"}
              </ActionButton>
              <ActionButton
                variant="ghost"
                onClick={handleBatchAnalyzeSelected}
                disabled={mutations.batchAnalyzeArticles.isPending || !selectedCount}
                className="h-11 justify-center"
              >
                <Sparkles size={14} className="mr-2" />
                {mutations.batchAnalyzeArticles.isPending
                  ? "正在总结已选..."
                  : selectedCount
                    ? `总结已选 ${selectedCount} 篇文章`
                    : "先勾选文章后再总结"}
              </ActionButton>
            </div>
          </div>
        </div>

        <div className="mt-5 rounded-[22px] border border-white/10 bg-black/25 p-4">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-white/42">Tags</p>
              <h3 className="mt-2 text-lg font-semibold text-white">文章标签筛选</h3>
              <p className="mt-2 max-w-2xl text-[13px] leading-6 text-white/52">
                输入关键词后从候选标签中选择。这里仅筛选文章标签，不会混入来源标签。
              </p>
            </div>
            {selectedTags.length ? (
              <ActionButton
                variant="ghost"
                onClick={() => {
                  setSelectedTags([]);
                  setTagQuery("");
                  resetPage();
                }}
              >
                <X size={14} className="mr-2" />
                清空已选标签
              </ActionButton>
            ) : null}
          </div>

          <div className="relative mt-5">
            <div className="rounded-[18px] border border-white/12 bg-white/6 px-4 py-3">
              <input
                value={tagQuery}
                onChange={(event) => setTagQuery(event.target.value)}
                onFocus={() => setTagPickerOpen(true)}
                placeholder="输入标签名称，按主题或层级路径搜索"
                className="w-full bg-transparent text-[13px] text-white outline-none placeholder:text-white/28"
              />
            </div>
            {tagPickerOpen ? (
              <div className="absolute left-0 right-0 z-20 mt-2 rounded-[18px] border border-white/12 bg-[#0d1524]/95 p-3 shadow-2xl backdrop-blur">
                <div className="flex items-center justify-between gap-3 px-1 pb-2">
                  <p className="text-xs uppercase tracking-[0.22em] text-white/38">Tag Library</p>
                  <button
                    type="button"
                    onClick={() => setTagPickerOpen(false)}
                    className="text-xs text-white/42 transition hover:text-white/72"
                  >
                    收起
                  </button>
                </div>
                <div className="max-h-72 overflow-y-auto pr-1">
                  {filteredTagOptions.length ? (
                    <div className="flex flex-wrap gap-2">
                      {filteredTagOptions.map((tag) => (
                        <button
                          key={tag}
                          type="button"
                          onMouseDown={(event) => event.preventDefault()}
                          onClick={() => addTag(tag)}
                          className="rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-xs text-white/74 transition hover:border-[#ffd478]/35 hover:bg-[#ffd478]/10 hover:text-[#ffe1a4]"
                        >
                          {tag}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="px-1 py-4 text-sm text-white/45">没有匹配到标签。</p>
                  )}
                </div>
              </div>
            ) : null}
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {selectedTags.length ? (
              selectedTags.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => removeTag(tag)}
                  className="rounded-full border border-[#ffd478]/35 bg-[#ffd478]/12 px-3 py-1.5 text-xs text-[#ffe1a4]"
                >
                  {tag}
                </button>
              ))
            ) : (
              <p className="text-sm text-white/42">还没有选择标签。点击输入框即可展开全部文章标签。</p>
            )}
          </div>
        </div>
      </section>

      <section className="mt-8">
        <SectionTitle title="文章列表" subtitle="列表聚焦文章本身的信息与标签，方便快速浏览和批量整理。" />
        {articles.isLoading ? (
          <EmptyState title="正在加载文章" description="正在整理当前筛选条件下的文章列表。" />
        ) : !currentItems.length ? (
          <EmptyState title="暂无文章" description="可以放宽筛选条件，或先去同步文章。" />
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <label className="inline-flex items-center gap-3 text-sm text-white/70">
                <input type="checkbox" checked={allCurrentPageSelected} onChange={toggleSelectCurrentPage} />
                选择当前页全部文章
              </label>
              <p className="text-sm text-white/55">
                第 {page} 页 / 共 {totalPages} 页
              </p>
            </div>
            <div className="grid gap-3 xl:grid-cols-2">
              {currentItems.map((article) => (
                <div
                  key={article.id}
                  className="rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(12,18,32,0.92),rgba(10,14,24,0.78))] p-4 shadow-[0_16px_44px_rgba(0,0,0,0.18)]"
                >
                  <div className="flex items-start justify-between gap-4">
                    <label className="flex min-w-0 items-start gap-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(article.id)}
                        onChange={() => toggleArticle(article.id)}
                        className="mt-1"
                      />
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-xs uppercase tracking-[0.28em] text-white/38">{article.source_name}</p>
                          <span className={`rounded-full border px-2.5 py-1 text-[11px] ${llmStatusTone(article.llm_summary_status)}`}>
                            {llmStatusLabel(article.llm_summary_status)}
                          </span>
                          {article.is_favorited ? <Star size={14} className="fill-[#ffd478] text-[#ffd478]" /> : null}
                        </div>
                        <Link href={`/articles/${article.id}`} className="mt-2 block text-[17px] leading-7 text-white hover:text-[#ffe1a4]">
                          {article.title}
                        </Link>
                      </div>
                    </label>
                    <div className="shrink-0 text-right">
                      <p className="text-xs text-white/38">{article.publish_time ?? "--"}</p>
                      <ActionButton
                        variant="danger"
                        className="mt-3"
                        onClick={() => handleDeleteOne(article.id, article.title)}
                        disabled={mutations.deleteArticle.isPending}
                      >
                        删除
                      </ActionButton>
                    </div>
                  </div>
                  {article.summary ? (
                    <div className="mt-4 rounded-[18px] border border-white/8 bg-white/4 px-4 py-3">
                      <p className="whitespace-pre-wrap break-words text-[13px] leading-6 text-white/68">{article.summary}</p>
                    </div>
                  ) : null}
                  <div className="mt-4">
                    <TagPills items={article.tags ?? []} />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
              <ActionButton variant="ghost" onClick={() => setPage((current) => Math.max(current - 1, 1))} disabled={page <= 1}>
                上一页
              </ActionButton>
              <p className="text-sm text-white/60">共找到 {total} 篇文章</p>
              <ActionButton
                variant="ghost"
                onClick={() => setPage((current) => Math.min(current + 1, totalPages))}
                disabled={page >= totalPages}
              >
                下一页
              </ActionButton>
            </div>
          </>
        )}
      </section>

      {/* Floating batch action bar */}
      {selectedIds.length > 0 ? (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2">
          <div className="flex items-center gap-3 rounded-[18px] border border-white/15 bg-[#0d1524]/90 px-4 py-3 shadow-2xl backdrop-blur">
            <span className="text-[13px] text-white/70">
              已选 <span className="font-semibold text-white">{selectedIds.length}</span> 篇
            </span>
            <div className="h-4 w-px bg-white/15" />
            <ActionButton
              variant="solid"
              onClick={handleBatchAnalyzeSelected}
              disabled={mutations.batchAnalyzeArticles.isPending}
            >
              <Sparkles size={13} className="mr-1.5" />
              总结已选
            </ActionButton>
            <ActionButton
              variant="danger"
              onClick={handleBatchDelete}
              disabled={mutations.batchDeleteArticles.isPending}
            >
              <Trash2 size={13} className="mr-1.5" />
              删除
            </ActionButton>
            <button
              type="button"
              onClick={() => setSelectedIds([])}
              className="ml-1 text-white/38 transition hover:text-white/72"
            >
              <X size={15} />
            </button>
          </div>
        </div>
      ) : null}
    </PageFrame>
  );
}

"use client";

import Link from "next/link";
import { useDeferredValue, useState } from "react";
import { RefreshCw, Search, Trash2 } from "lucide-react";
import { useArticles, useMutations, useSources } from "@/lib/queries";
import { ActionButton, EmptyState, Input, PageFrame, SectionTitle, TagPills } from "@/components/ui";

export default function ArticlesPage() {
  const sources = useSources();
  const mutations = useMutations();

  const [sourceId, setSourceId] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<"latest" | "oldest">("latest");
  const [pageSize, setPageSize] = useState(24);
  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const deferredQuery = useDeferredValue(query);
  const articles = useArticles({
    sourceId: sourceId || undefined,
    q: deferredQuery.trim() || undefined,
    page,
    pageSize,
    sort,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
  });

  const currentItems = articles.data?.items ?? [];
  const total = articles.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const allCurrentPageSelected = currentItems.length > 0 && currentItems.every((item) => selectedIds.includes(item.id));

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
  }

  return (
    <PageFrame
      title="文章浏览"
      subtitle="按来源、关键词和时间区间筛选文章，支持总量统计、单篇删除和批量删除。"
      actions={
        <>
          <ActionButton variant="ghost" onClick={() => articles.refetch()}>
            <RefreshCw size={14} className="mr-2" />
            刷新列表
          </ActionButton>
          <ActionButton
            variant="danger"
            onClick={handleBatchDelete}
            disabled={!selectedIds.length || mutations.batchDeleteArticles.isPending}
          >
            <Trash2 size={14} className="mr-2" />
            批量删除
          </ActionButton>
        </>
      }
    >
      <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
        <SectionTitle title="筛选条件" subtitle="先按时间和来源收窄范围，再用关键词精确检索。" />
        <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr_0.7fr]">
          <div>
            <label className="mb-2 block text-sm text-white/75">关键词</label>
            <div className="flex gap-3">
              <Input
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  resetPage();
                }}
                placeholder="搜索标题、摘要、正文或来源名称"
              />
              <ActionButton variant="ghost" onClick={() => articles.refetch()}>
                <Search size={14} className="mr-2" />
                搜索
              </ActionButton>
            </div>
          </div>
          <div>
            <label className="mb-2 block text-sm text-white/75">来源</label>
            <select
              value={sourceId}
              onChange={(event) => {
                setSourceId(event.target.value);
                resetPage();
              }}
              className="w-full rounded-2xl border border-white/12 bg-white/5 px-4 py-3 text-sm text-white outline-none"
            >
              <option value="">全部来源</option>
              {(sources.data ?? []).map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm text-white/75">起始日期</label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(event) => {
                  setDateFrom(event.target.value);
                  resetPage();
                }}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm text-white/75">结束日期</label>
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
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-5">
          <div>
            <label className="mb-2 block text-sm text-white/75">排序</label>
            <select
              value={sort}
              onChange={(event) => {
                setSort(event.target.value as "latest" | "oldest");
                resetPage();
              }}
              className="w-full rounded-2xl border border-white/12 bg-white/5 px-4 py-3 text-sm text-white outline-none"
            >
              <option value="latest">按发布时间倒序</option>
              <option value="oldest">按发布时间正序</option>
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm text-white/75">每页条数</label>
            <select
              value={pageSize}
              onChange={(event) => {
                setPageSize(Number(event.target.value) || 24);
                resetPage();
              }}
              className="w-full rounded-2xl border border-white/12 bg-white/5 px-4 py-3 text-sm text-white outline-none"
            >
              <option value={12}>12</option>
              <option value={24}>24</option>
              <option value={48}>48</option>
              <option value={100}>100</option>
            </select>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.28em] text-white/40">文章总数</p>
            <p className="mt-2 text-xl font-semibold text-white">{total}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.28em] text-white/40">当前页</p>
            <p className="mt-2 text-xl font-semibold text-white">
              {page} / {totalPages}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.28em] text-white/40">已选择</p>
            <p className="mt-2 text-xl font-semibold text-white">{selectedIds.length}</p>
          </div>
        </div>
      </section>

      <section className="mt-8">
        <SectionTitle title="文章列表" subtitle="当前页支持全选和批量删除，点击标题进入详情页。" />
        {articles.isLoading ? (
          <EmptyState title="正在加载文章" description="后端正在返回当前筛选条件下的文章列表。" />
        ) : !currentItems.length ? (
          <EmptyState title="暂无文章" description="可以放宽时间区间、切换来源，或者先去采集页同步文章。" />
        ) : (
          <>
            <div className="mb-4 flex items-center justify-between gap-3">
              <label className="inline-flex items-center gap-3 text-sm text-white/70">
                <input type="checkbox" checked={allCurrentPageSelected} onChange={toggleSelectCurrentPage} />
                选择当前页全部文章
              </label>
              <p className="text-sm text-white/55">当前条件下共 {total} 篇文章</p>
            </div>
            <div className="grid gap-4 xl:grid-cols-2">
              {currentItems.map((article) => (
                <div key={article.id} className="rounded-[28px] border border-white/10 bg-black/20 p-5">
                  <div className="flex items-start justify-between gap-4">
                    <label className="flex items-start gap-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(article.id)}
                        onChange={() => toggleArticle(article.id)}
                        className="mt-1"
                      />
                      <div>
                        <p className="text-xs uppercase tracking-[0.28em] text-white/40">{article.source_name}</p>
                        <Link href={`/articles/${article.id}`} className="mt-2 block text-lg leading-7 text-white hover:underline">
                          {article.title}
                        </Link>
                      </div>
                    </label>
                    <div className="text-right">
                      <p className="text-xs text-white/40">{article.publish_time ?? "--"}</p>
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
                  {article.summary ? <p className="mt-4 line-clamp-4 text-sm leading-6 text-white/65">{article.summary}</p> : null}
                  <div className="mt-4">
                    <TagPills items={[...article.topic_tags.slice(0, 4), ...article.source_tags.slice(0, 3)]} />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
              <ActionButton variant="ghost" onClick={() => setPage((current) => Math.max(current - 1, 1))} disabled={page <= 1}>
                上一页
              </ActionButton>
              <p className="text-sm text-white/60">
                第 {page} 页 / 共 {totalPages} 页
              </p>
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
    </PageFrame>
  );
}

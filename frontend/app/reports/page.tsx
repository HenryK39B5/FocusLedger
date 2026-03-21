"use client";

import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { useDailyReport, useSources } from "@/lib/queries";
import { ActionButton, EmptyState, Input, PageFrame, SectionTitle, TagPills } from "@/components/ui";

function getLocalDateInput() {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

export default function ReportsPage() {
  const sources = useSources();
  const [date, setDate] = useState(getLocalDateInput());
  const [sourceId, setSourceId] = useState("");
  const [sourceGroup, setSourceGroup] = useState("");
  const [limit, setLimit] = useState(20);

  const report = useDailyReport({
    date,
    sourceId: sourceId || undefined,
    sourceGroup: sourceGroup || undefined,
    limit,
  });

  const sourceGroups = useMemo(() => {
    const groups = new Set<string>();
    for (const source of sources.data ?? []) {
      if (source.source_group) {
        groups.add(source.source_group);
      }
    }
    return Array.from(groups).sort((a, b) => a.localeCompare(b, "zh-Hans-CN"));
  }, [sources.data]);

  const articleMap = useMemo(() => {
    return new Map((report.data?.articles ?? []).map((article) => [article.id, article]));
  }, [report.data?.articles]);

  return (
    <PageFrame
      title="日报生成"
      subtitle="按日期、来源和来源分组生成公众号日报。日报会综合来源分组、来源标签、文章摘要和文章标签来组织内容。"
      actions={
        <ActionButton variant="ghost" onClick={() => report.refetch()}>
          <RefreshCw size={14} className="mr-2" />
          重新生成
        </ActionButton>
      }
    >
      <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
        <SectionTitle title="生成参数" subtitle="默认按当天生成日报，也可以限定单一来源或分组。" />
        <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr_0.7fr_0.6fr]">
          <div>
            <label className="mb-2 block text-sm text-white/75">日期</label>
            <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          </div>
          <div>
            <label className="mb-2 block text-sm text-white/75">来源</label>
            <select
              value={sourceId}
              onChange={(event) => setSourceId(event.target.value)}
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
          <div>
            <label className="mb-2 block text-sm text-white/75">来源分组</label>
            <select
              value={sourceGroup}
              onChange={(event) => setSourceGroup(event.target.value)}
              className="w-full rounded-2xl border border-white/12 bg-white/5 px-4 py-3 text-sm text-white outline-none"
            >
              <option value="">全部分组</option>
              {sourceGroups.map((group) => (
                <option key={group} value={group}>
                  {group}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm text-white/75">文章上限</label>
            <select
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value) || 20)}
              className="w-full rounded-2xl border border-white/12 bg-white/5 px-4 py-3 text-sm text-white outline-none"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={30}>30</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>
      </section>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.35fr_0.9fr]">
        <div className="space-y-6">
          <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <SectionTitle title="日报正文" subtitle="适合直接阅读，也适合继续整理成晨报或复盘邮件。" />
            {report.isLoading ? (
              <EmptyState title="正在生成日报" description="系统正在汇总指定日期的文章并生成结构化日报。" />
            ) : report.isError ? (
              <EmptyState title="日报生成失败" description="请确认这一天已有同步文章，并检查后端服务与 LLM 配置。" />
            ) : report.data ? (
              <div className="space-y-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-white/40">{report.data.date}</p>
                  <h3 className="mt-2 text-2xl font-semibold text-white">{report.data.title}</h3>
                </div>
                {report.data.overview ? <p className="text-sm leading-7 text-white/70">{report.data.overview}</p> : null}
                <div className="rounded-[24px] border border-white/10 bg-black/20 p-5">
                  <pre className="whitespace-pre-wrap text-sm leading-7 text-white/72">{report.data.report_markdown}</pre>
                </div>
              </div>
            ) : null}
          </section>

          <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <SectionTitle title="日报分区" subtitle="每个分区都关联具体文章，方便继续下钻。" />
            {report.data?.sections?.length ? (
              <div className="space-y-4">
                {report.data.sections.map((section) => (
                  <div key={section.title} className="rounded-[24px] border border-white/10 bg-black/20 p-5">
                    <h4 className="text-lg font-medium text-white">{section.title}</h4>
                    {section.summary ? <p className="mt-3 text-sm leading-6 text-white/65">{section.summary}</p> : null}
                    {section.bullets.length ? (
                      <ul className="mt-4 space-y-2 text-sm leading-6 text-white/72">
                        {section.bullets.map((bullet, index) => (
                          <li key={`${section.title}-${index}`}>- {bullet}</li>
                        ))}
                      </ul>
                    ) : null}
                    {section.article_ids.length ? (
                      <div className="mt-5 grid gap-3 lg:grid-cols-2">
                        {section.article_ids.map((articleId) => {
                          const article = articleMap.get(articleId);
                          if (!article) {
                            return null;
                          }
                          return (
                            <Link
                              key={article.id}
                              href={`/articles/${article.id}`}
                              className="rounded-[20px] border border-white/10 bg-white/5 p-4 transition hover:border-white/20 hover:bg-white/8"
                            >
                              <p className="text-base text-white">{article.title}</p>
                              <p className="mt-2 text-xs text-white/45">{article.source_name}</p>
                              {article.summary ? <p className="mt-3 line-clamp-3 text-sm leading-6 text-white/62">{article.summary}</p> : null}
                            </Link>
                          );
                        })}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="暂无分区内容" description="如果当天没有匹配文章，日报不会生成分区。" />
            )}
          </section>
        </div>

        <div className="space-y-6">
          <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <SectionTitle title="日报统计" subtitle="快速判断当天内容的覆盖情况。" />
            {report.data ? (
              <div className="grid gap-3">
                <div className="rounded-[20px] border border-white/10 bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.28em] text-white/40">匹配文章</p>
                  <p className="mt-3 text-2xl font-semibold text-white">{String(report.data.stats.matched_articles ?? 0)}</p>
                </div>
                <div className="rounded-[20px] border border-white/10 bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.28em] text-white/40">纳入日报</p>
                  <p className="mt-3 text-2xl font-semibold text-white">{String(report.data.stats.selected_articles ?? 0)}</p>
                </div>
                <div className="rounded-[20px] border border-white/10 bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.28em] text-white/40">分组数</p>
                  <p className="mt-3 text-2xl font-semibold text-white">{String(report.data.stats.source_group_count ?? 0)}</p>
                </div>
              </div>
            ) : (
              <EmptyState title="还没有日报" description="选择日期后，系统会自动生成日报。" />
            )}
          </section>

          <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <SectionTitle title="后续关注" subtitle="日报提炼出的继续跟踪项。" />
            {report.data?.follow_ups?.length ? (
              <TagPills items={report.data.follow_ups} />
            ) : (
              <EmptyState title="暂无跟踪项" description="当前日报没有输出单独的后续关注点。" />
            )}
          </section>
        </div>
      </div>
    </PageFrame>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";

import { ActionButton, EmptyState, Input, Label, PageFrame, SectionTitle, TagPills } from "@/components/ui";
import { useDailyReport, useSources } from "@/lib/queries";

function todayInShanghai() {
  const now = new Date();
  const local = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Shanghai" }));
  return local.toISOString().slice(0, 10);
}

export default function ReportsPage() {
  const sources = useSources();
  const sourceItems = sources.data ?? [];

  const [date, setDate] = useState(todayInShanghai);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [sourceGroup, setSourceGroup] = useState("");
  const [limit, setLimit] = useState("20");
  const [submitted, setSubmitted] = useState({
    date: todayInShanghai(),
    sourceId: "",
    sourceGroup: "",
    limit: 20,
  });

  const knownGroups = useMemo(() => {
    const seen = new Set<string>();
    for (const source of sourceItems) {
      const group = (source.source_group ?? "").trim();
      if (group) seen.add(group);
    }
    return Array.from(seen).sort((a, b) => a.localeCompare(b, "zh-CN"));
  }, [sourceItems]);

  useEffect(() => {
    if (!selectedSourceId) {
      return;
    }
    const source = sourceItems.find((item) => item.id === selectedSourceId);
    if (source?.source_group) {
      setSourceGroup(source.source_group);
    }
  }, [selectedSourceId, sourceItems]);

  const report = useDailyReport({
    date: submitted.date,
    sourceId: submitted.sourceId || undefined,
    sourceGroup: submitted.sourceGroup || undefined,
    limit: submitted.limit,
    enabled: Boolean(submitted.date),
  });

  const activeSource = sourceItems.find((item) => item.id === submitted.sourceId);
  const matchedCount = Number(report.data?.stats?.matched_articles ?? 0);
  const selectedCount = Number(report.data?.stats?.selected_articles ?? 0);

  return (
    <PageFrame
      title="日报生成"
      subtitle="按日期、来源或来源分组汇总当天文章，生成可读的日报文本，也可供 QClaw 调用。"
      actions={
        <ActionButton
          type="button"
          onClick={() =>
            setSubmitted({
              date,
              sourceId: selectedSourceId,
              sourceGroup: sourceGroup.trim(),
              limit: Math.max(1, Number(limit) || 20),
            })
          }
        >
          生成日报
        </ActionButton>
      }
    >
      <section className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle title="筛选条件" subtitle="先选日期，再按需要收窄到单一来源或分组。" />

          <div className="space-y-4">
            <div>
              <Label>日期</Label>
              <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
            </div>

            <div>
              <Label>来源</Label>
              <select
                value={selectedSourceId}
                onChange={(event) => setSelectedSourceId(event.target.value)}
                className="w-full rounded-[18px] border border-white/12 bg-white/5 px-3.5 py-2.5 text-[13px] text-white outline-none focus:border-white/24"
              >
                <option value="" className="bg-slate-900">
                  全部来源
                </option>
                {sourceItems.map((source) => (
                  <option key={source.id} value={source.id} className="bg-slate-900">
                    {source.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <Label>来源分组</Label>
              <Input
                list="report-source-groups"
                value={sourceGroup}
                onChange={(event) => setSourceGroup(event.target.value)}
                placeholder="例如 投研/科技/AI"
              />
              <datalist id="report-source-groups">
                {knownGroups.map((group) => (
                  <option key={group} value={group} />
                ))}
              </datalist>
            </div>

            <div>
              <Label>文章上限</Label>
              <Input
                type="number"
                min={1}
                max={50}
                value={limit}
                onChange={(event) => setLimit(event.target.value)}
              />
            </div>
          </div>

          <div className="mt-6 rounded-[22px] border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-white/38">当前范围</p>
            <div className="mt-3 space-y-2 text-sm text-white/68">
              <p>日期：{submitted.date}</p>
              <p>来源：{activeSource?.name ?? "全部来源"}</p>
              <p>分组：{submitted.sourceGroup || "不限分组"}</p>
              <p>上限：{submitted.limit} 篇</p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <SectionTitle
                  title={report.data?.title ?? "日报结果"}
                  subtitle={report.isLoading ? "正在生成日报..." : "生成后的概要、重点和原始文章都会展示在这里。"}
                />
              </div>
              <div className="flex gap-3">
                <div className="rounded-[18px] border border-white/10 bg-black/20 px-4 py-3 text-center">
                  <div className="text-lg font-semibold text-white">{matchedCount}</div>
                  <div className="text-xs text-white/42">匹配文章</div>
                </div>
                <div className="rounded-[18px] border border-white/10 bg-black/20 px-4 py-3 text-center">
                  <div className="text-lg font-semibold text-white">{selectedCount}</div>
                  <div className="text-xs text-white/42">纳入日报</div>
                </div>
              </div>
            </div>

            {report.isError ? (
              <EmptyState title="日报生成失败" description={report.error instanceof Error ? report.error.message : "请稍后重试。"} />
            ) : null}

            {!report.isError && !report.isLoading && report.data && matchedCount <= 0 ? (
              <EmptyState title="当天没有匹配文章" description="先同步来源文章，或者换一个日期、来源范围再试。" />
            ) : null}

            {!report.isError && report.data && matchedCount > 0 ? (
              <div className="space-y-5">
                {report.data.overview ? (
                  <div className="rounded-[22px] border border-[#f7c66b]/18 bg-[#f7c66b]/8 p-4 text-sm leading-7 text-white/82">
                    {report.data.overview}
                  </div>
                ) : null}

                <div className="grid gap-4 xl:grid-cols-2">
                  {report.data.sections.map((section, index) => (
                    <article key={`${section.title}-${index}`} className="rounded-[22px] border border-white/10 bg-black/20 p-4">
                      <p className="text-xs uppercase tracking-[0.24em] text-[#f7c66b]/80">重点 {index + 1}</p>
                      <h3 className="mt-2 text-lg text-white">{section.title}</h3>
                      {section.summary ? <p className="mt-3 text-sm leading-6 text-white/64">{section.summary}</p> : null}
                      {section.bullets.length ? (
                        <ul className="mt-4 space-y-2 text-sm leading-6 text-white/76">
                          {section.bullets.map((bullet, bulletIndex) => (
                            <li key={`${section.title}-${bulletIndex}`}>- {bullet}</li>
                          ))}
                        </ul>
                      ) : null}
                    </article>
                  ))}
                </div>

                {report.data.follow_ups.length ? (
                  <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
                    <SectionTitle title="后续关注" />
                    <div className="space-y-2 text-sm leading-6 text-white/76">
                      {report.data.follow_ups.map((item, index) => (
                        <p key={`${item}-${index}`}>- {item}</p>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>

          <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <SectionTitle title="纳入文章" subtitle="这里展示进入日报的文章，便于回看来源、标签和摘要。" />

            {report.data?.articles.length ? (
              <div className="space-y-3">
                {report.data.articles.map((article) => (
                  <article key={article.id} className="rounded-[22px] border border-white/10 bg-black/20 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.22em] text-white/38">{article.source_name}</p>
                        <h3 className="mt-2 text-base leading-7 text-white">{article.title}</h3>
                      </div>
                      <div className="text-right text-xs text-white/42">
                        <p>{article.publish_time ?? "--"}</p>
                        <p className="mt-1">权重 {article.importance_score.toFixed(2)}</p>
                      </div>
                    </div>
                    {article.summary ? <p className="mt-3 text-sm leading-6 text-white/64">{article.summary}</p> : null}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <TagPills items={[...(article.source_tags ?? []), ...(article.topic_tags ?? []).slice(0, 4)]} />
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState title="还没有纳入文章" description="生成成功后，这里会展示日报覆盖到的文章列表。" />
            )}
          </section>
        </div>
      </section>
    </PageFrame>
  );
}

"use client";

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import { useArticles, useSources } from "@/lib/queries";
import { ActionButton, EmptyState, PageFrame, StatCard, TagPills } from "@/components/ui";
import { credentialStatusLabel } from "@/lib/wechat";

function countByStatus(statuses: string[], target: string) {
  return statuses.filter((status) => status === target).length;
}

export default function HomePage() {
  const sources = useSources();
  const articles = useArticles({ page: 1, pageSize: 6, sort: "latest" });

  const sourceItems = sources.data ?? [];
  const articleItems = articles.data?.items ?? [];
  const sourceStatuses = sourceItems.map((source) => source.credential_status);

  return (
    <PageFrame
      title="研究台总览"
      subtitle="围绕公众号来源、文章库和日报输出组织你的本地研究工作流。"
      actions={
        <>
          <Link href="/sources/add">
            <ActionButton variant="ghost">添加来源</ActionButton>
          </Link>
          <Link href="/articles">
            <ActionButton variant="solid">
              进入文章库
              <ArrowRight size={14} className="ml-2" />
            </ActionButton>
          </Link>
        </>
      }
    >
      <section className="overflow-hidden rounded-[30px] border border-white/10 bg-[linear-gradient(140deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-6 lg:p-8">
        <div className="grid gap-8 xl:grid-cols-[1.15fr_0.85fr]">
          <div>
            <p className="text-xs uppercase tracking-[0.34em] text-white/42">FocusLedger / Research Desk</p>
            <h3 className="mt-4 max-w-3xl font-[family-name:var(--font-display)] text-4xl leading-[1.08] text-white lg:text-5xl">
              先沉淀文章，
              <br />
              再提炼观点。
            </h3>
            <p className="mt-5 max-w-2xl text-base leading-7 text-white/62">
              这里不是一个简单的抓取页，而是一套围绕公众号文章建立的本地研究台。来源同步、标签整理、文章收藏和日报输出，都在同一条路径里完成。
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/collect">
                <ActionButton variant="solid">开始同步文章</ActionButton>
              </Link>
              <Link href="/reports">
                <ActionButton variant="ghost">查看日报能力</ActionButton>
              </Link>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <div className="rounded-[24px] border border-white/10 bg-black/20 p-5">
              <div className="flex items-center gap-2 text-sm text-white/72">
                <Sparkles size={14} />
                当前重点
              </div>
              <div className="mt-4 space-y-3 text-sm leading-6 text-white/60">
                <p>文章管理层已经独立出 LLM 总结流程，后续可以更稳定地支撑收藏、标签和 Notebook。</p>
                <p>同步凭据保持手动更新，产品价值放在本地知识库和研究工作区上。</p>
              </div>
            </div>
            <div className="rounded-[24px] border border-white/10 bg-white/5 p-5">
              <p className="text-xs uppercase tracking-[0.28em] text-white/45">来源状态</p>
              <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-4">
                  <div className="text-xl font-semibold text-white">{countByStatus(sourceStatuses, "valid")}</div>
                  <div className="mt-1 text-xs text-white/45">可用</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-4">
                  <div className="text-xl font-semibold text-white">{countByStatus(sourceStatuses, "refresh_required")}</div>
                  <div className="mt-1 text-xs text-white/45">待更新</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-4">
                  <div className="text-xl font-semibold text-white">{countByStatus(sourceStatuses, "invalid")}</div>
                  <div className="mt-1 text-xs text-white/45">失效</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <StatCard label="公众号来源" value={String(sourceItems.length)} hint="当前已保存的来源总数" />
        <StatCard label="文章总量" value={String(articles.data?.total ?? 0)} hint="文章库中可继续整理的文章" />
        <StatCard label="最近同步提醒" value={String(countByStatus(sourceStatuses, "refresh_required"))} hint="需要手动更新凭据的来源数" />
      </div>

      <div className="mt-8 grid gap-6 2xl:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold text-white">最近文章</h3>
              <p className="mt-1 text-sm text-white/55">从这里进入阅读和后续整理。</p>
            </div>
            <Link href="/articles" className="text-sm text-[#ffd478] hover:underline">
              浏览全部
            </Link>
          </div>

          {articleItems.length ? (
            <div className="grid gap-4 xl:grid-cols-2">
              {articleItems.map((article) => (
                <Link
                  key={article.id}
                  href={`/articles/${article.id}`}
                  className="rounded-[24px] border border-white/10 bg-black/20 p-5 transition hover:border-white/20 hover:bg-black/30"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.24em] text-white/38">{article.source_name}</p>
                      <h4 className="mt-2 text-lg leading-7 text-white">{article.title}</h4>
                    </div>
                    <p className="shrink-0 text-xs text-white/40">{article.publish_time ?? "--"}</p>
                  </div>
                  {article.summary ? <p className="mt-4 line-clamp-3 text-sm leading-6 text-white/62">{article.summary}</p> : null}
                  <div className="mt-4 flex flex-wrap gap-2">
                    <TagPills items={[...(article.tags ?? []).slice(0, 4), ...(article.content_type ? [article.content_type] : [])]} />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState title="暂无文章" description="先去“文章获取”同步真实文章，再回到这里浏览和整理。" />
          )}
        </section>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold text-white">来源概览</h3>
              <p className="mt-1 text-sm text-white/55">快速查看来源健康状态和标签结构。</p>
            </div>
            <Link href="/sources" className="text-sm text-[#ffd478] hover:underline">
              管理来源
            </Link>
          </div>

          {sourceItems.length ? (
            <div className="space-y-3">
              {sourceItems.slice(0, 6).map((source) => (
                <div key={source.id} className="rounded-[22px] border border-white/10 bg-black/20 px-4 py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="truncate text-sm font-medium text-white">{source.name}</h4>
                        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-white/68">
                          {credentialStatusLabel(source.credential_status)}
                        </span>
                      </div>
                      {source.source_group ? <p className="mt-2 text-xs text-white/40">{source.source_group}</p> : null}
                    </div>
                  </div>
                  {source.tags.length ? (
                    <div className="mt-3">
                      <TagPills items={source.tags.slice(0, 5)} />
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="暂无来源" description="先添加来源，再逐步建立你的文章库。" />
          )}
        </section>
      </div>
    </PageFrame>
  );
}

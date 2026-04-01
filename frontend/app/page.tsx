"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useArticles, useSources } from "@/lib/queries";
import { ActionButton, EmptyState, PageFrame, SectionTitle, StatCard, TagPills } from "@/components/ui";
import { credentialStatusLabel } from "@/lib/wechat";

export default function HomePage() {
  const sources = useSources();
  const articles = useArticles({ page: 1, pageSize: 6, sort: "latest" });

  const refreshRequiredCount = (sources.data ?? []).filter((source) => source.credential_status === "refresh_required").length;

  return (
    <PageFrame
      title="公众号研究总览"
      subtitle="这里汇总当前系统的来源规模、文章规模和最近文章。来源添加、文章获取、文章浏览和日报生成分别独立。"
      actions={
        <>
          <Link href="/sources/add">
            <ActionButton variant="ghost">添加公众号来源</ActionButton>
          </Link>
          <Link href="/reports">
            <ActionButton variant="solid">
              生成日报
              <ArrowRight size={14} className="ml-2" />
            </ActionButton>
          </Link>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="公众号来源" value={String(sources.data?.length ?? 0)} hint="已保存的公众号来源总数" />
        <StatCard label="文章总量" value={String(articles.data?.total ?? 0)} hint="数据库中可浏览的文章总数" />
        <StatCard label="待刷新来源" value={String(refreshRequiredCount)} hint="当前凭据已失效或需要更新的来源数" />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.2fr_0.9fr]">
        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle title="最近文章" subtitle="最新入库文章可直接进入详情页查看摘要、标签和正文。" />
          {articles.data?.items?.length ? (
            <div className="space-y-4">
              {articles.data.items.map((article) => (
                <Link
                  key={article.id}
                  href={`/articles/${article.id}`}
                  className="block rounded-[24px] border border-white/10 bg-black/20 p-5 transition hover:border-white/20 hover:bg-black/30"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.28em] text-white/40">{article.source_name}</p>
                      <h3 className="mt-2 text-lg leading-7 text-white">{article.title}</h3>
                    </div>
                    <p className="text-xs text-white/45">{article.publish_time ?? "--"}</p>
                  </div>
                  {article.summary ? <p className="mt-4 line-clamp-3 text-sm leading-6 text-white/65">{article.summary}</p> : null}
                  <div className="mt-4">
                    <TagPills items={[...article.topic_tags.slice(0, 4), ...article.source_tags.slice(0, 2)]} />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState title="暂无文章" description="先去“文章获取”页面同步文章，再回到这里查看。" />
          )}
        </section>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle title="来源概览" subtitle="这里只展示来源状态和标签。详细维护请进入来源管理页。" />
          {sources.data?.length ? (
            <div className="space-y-4">
              {sources.data.slice(0, 6).map((source) => (
                <div key={source.id} className="rounded-[24px] border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm text-white">{source.name}</p>
                    <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-white/70">
                      {credentialStatusLabel(source.credential_status)}
                    </span>
                  </div>
                  {source.description ? <p className="mt-2 text-sm leading-6 text-white/60">{source.description}</p> : null}
                  {source.tags.length ? (
                    <div className="mt-3">
                      <TagPills items={source.tags} />
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="暂无来源" description="先去“添加公众号来源”页面创建一个来源，再同步文章。" />
          )}
        </section>
      </div>
    </PageFrame>
  );
}

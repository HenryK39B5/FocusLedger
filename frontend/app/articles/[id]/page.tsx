"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ExternalLink, Trash2 } from "lucide-react";
import { useMemo } from "react";
import { useArticle, useMutations } from "@/lib/queries";
import { ActionButton, EmptyState, PageFrame, SectionTitle, TagPills } from "@/components/ui";

function getMetadataString(metadata: Record<string, unknown>, key: string) {
  const value = metadata[key];
  return typeof value === "string" ? value : "";
}

function formatTextForDisplay(text: string) {
  const normalized = text.replace(/\r\n?/g, "\n").trim();
  const blocks = normalized
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);

  if (blocks.length > 1) {
    return blocks;
  }

  const lines = normalized
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const paragraphs: string[] = [];
  let buffer = "";
  for (const line of lines) {
    const looksComplete = /[。！？；：.!?]$/.test(line) || line.length >= 48;
    if (!looksComplete) {
      buffer = buffer ? `${buffer}${line}` : line;
      continue;
    }
    paragraphs.push(buffer ? `${buffer}${line}` : line);
    buffer = "";
  }
  if (buffer) {
    paragraphs.push(buffer);
  }
  return paragraphs.length ? paragraphs : [normalized];
}

export default function ArticleDetailPage() {
  const params = useParams<{ id: string }>();
  const article = useArticle(params.id);
  const mutations = useMutations();

  const paragraphs = useMemo(() => {
    if (!article.data?.raw_text) {
      return [];
    }
    return formatTextForDisplay(article.data.raw_text);
  }, [article.data?.raw_text]);

  if (article.isLoading) {
    return (
      <PageFrame title="文章详情" subtitle="正在加载文章内容">
        <EmptyState title="加载中" description="请稍候。" />
      </PageFrame>
    );
  }

  if (article.isError || !article.data) {
    return (
      <PageFrame title="文章详情" subtitle="文章详情页">
        <EmptyState title="文章不存在" description="请回到文章浏览页重新选择，或确认这篇文章未被删除。" />
      </PageFrame>
    );
  }

  const data = article.data;
  const metadata = data.metadata_json ?? {};
  const originalUrl = getMetadataString(metadata, "raw_article_url") || data.url;
  const homeLink = getMetadataString(metadata, "public_home_link");

  return (
    <PageFrame
      title="文章详情"
      subtitle="这里只保留原文链接，不暴露抓取地址和规范化 URL。摘要和正文都按阅读视图展示。"
      actions={
        <>
          <Link href="/articles">
            <ActionButton variant="ghost">
              <ArrowLeft size={14} className="mr-2" />
              返回文章浏览
            </ActionButton>
          </Link>
          <ActionButton
            variant="danger"
            onClick={async () => {
              if (!window.confirm(`确认删除文章《${data.title}》吗？`)) {
                return;
              }
              await mutations.deleteArticle.mutateAsync(data.id);
              window.location.href = "/articles";
            }}
            disabled={mutations.deleteArticle.isPending}
          >
            <Trash2 size={14} className="mr-2" />
            删除文章
          </ActionButton>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[1.45fr_0.9fr]">
        <div className="space-y-6">
          <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
            <p className="text-sm text-white/50">{data.source?.name ?? "未知来源"}</p>
            <h3 className="mt-2 text-3xl font-semibold leading-tight text-white">{data.title}</h3>
            <p className="mt-4 text-sm text-white/55">
              作者：{data.author ?? "未知"} · 发布时间：{data.publish_time ?? "未知"}
            </p>

            <div className="mt-5">
              <TagPills items={[...data.topic_tags, ...data.style_tags]} />
            </div>

            <div className="mt-6 grid gap-3 rounded-[24px] border border-white/10 bg-black/20 p-4 text-sm text-white/70 md:grid-cols-2">
              <div>
                <p className="text-white/45">原文链接</p>
                <a
                  href={originalUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-flex items-center gap-2 text-[#ffd478] hover:underline"
                >
                  查看原文
                  <ExternalLink size={14} />
                </a>
              </div>
              <div>
                <p className="text-white/45">公众号主页</p>
                {homeLink ? (
                  <a
                    href={homeLink}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex items-center gap-2 text-[#ffd478] hover:underline"
                  >
                    打开主页
                    <ExternalLink size={14} />
                  </a>
                ) : (
                  <p className="mt-1 text-white/60">未提取到主页链接</p>
                )}
              </div>
            </div>
          </section>

          <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
            <SectionTitle title="摘要" subtitle="摘要优先来自 LLM 整理；LLM 不可用时回退到规则版摘要。" />
            <div className="rounded-[24px] border border-white/10 bg-black/20 p-5">
              <p className="whitespace-pre-wrap text-sm leading-8 text-white/72">{data.summary ?? "暂无摘要"}</p>
            </div>
          </section>

          <section className="rounded-[28px] border border-white/10 bg-white/5 p-6">
            <SectionTitle
              title="正文"
              subtitle="正文优先从微信正文区提取，再经过清洗与分段。旧文章如果还没回填，页面也会做一次轻量排版。"
            />
            <div className="rounded-[28px] border border-white/10 bg-[#0b1220]/80 px-6 py-7">
              {paragraphs.length ? (
                <div className="mx-auto max-w-4xl space-y-6">
                  {paragraphs.map((paragraph, index) => (
                    <p key={index} className="text-[15px] leading-8 text-white/78">
                      {paragraph}
                    </p>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-white/60">暂无正文文本</p>
              )}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <SectionTitle title="结构化信息" subtitle="文章标签和关键信息会集中展示在这里。" />
            <div className="space-y-4 text-sm text-white/70">
              <div>
                <p className="text-white">内容类型</p>
                <p className="mt-2">{data.content_type ?? "未识别"}</p>
              </div>
              <div>
                <p className="text-white">主题标签</p>
                <div className="mt-3">
                  <TagPills items={data.topic_tags} />
                </div>
              </div>
              <div>
                <p className="text-white">实体标签</p>
                <div className="mt-3">
                  <TagPills items={data.entity_tags} />
                </div>
              </div>
              <div>
                <p className="text-white">核心观点</p>
                <div className="mt-3 space-y-2">
                  {data.core_claims.length ? (
                    data.core_claims.map((claim, index) => (
                      <p key={index} className="rounded-2xl border border-white/10 bg-black/20 p-3">
                        {claim}
                      </p>
                    ))
                  ) : (
                    <p className="text-white/55">暂无提取结果</p>
                  )}
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
            <SectionTitle title="跟踪维度" subtitle="把变量、催化和风险拆开，便于后续日报归纳。" />
            <div className="space-y-4 text-sm text-white/70">
              <div>
                <p className="text-white">关键变量</p>
                <div className="mt-3">
                  <TagPills items={data.key_variables} />
                </div>
              </div>
              <div>
                <p className="text-white">催化因素</p>
                <div className="mt-3">
                  <TagPills items={data.catalysts} />
                </div>
              </div>
              <div>
                <p className="text-white">风险项</p>
                <div className="mt-3">
                  <TagPills items={data.risks} />
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </PageFrame>
  );
}

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ExternalLink, Save, Sparkles, Star, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useArticle, useMutations } from "@/lib/queries";
import { ActionButton, EmptyState, Input, Label, PageFrame, SectionTitle, TagPills } from "@/components/ui";
import { formatDateTimeShanghai } from "@/lib/wechat";

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
    const looksComplete = /[。！？；?!]$/.test(line) || line.length >= 48;
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

function parseTags(value: string) {
  return value
    .split(/[,\n，]/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .filter((tag, index, list) => list.indexOf(tag) === index);
}

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

export default function ArticleDetailPage() {
  const params = useParams<{ id: string }>();
  const article = useArticle(params.id);
  const mutations = useMutations();

  const [tagsDraft, setTagsDraft] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!article.data) {
      return;
    }
    setTagsDraft((article.data.tags ?? []).join(", "));
  }, [article.data]);

  const paragraphs = useMemo(() => {
    if (!article.data?.raw_text) {
      return [];
    }
    return formatTextForDisplay(article.data.raw_text);
  }, [article.data?.raw_text]);

  const summaryParagraphs = useMemo(() => {
    if (!article.data?.summary) {
      return [];
    }
    return formatTextForDisplay(article.data.summary);
  }, [article.data?.summary]);

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

  async function handleSave() {
    try {
      await mutations.updateArticle.mutateAsync({
        articleId: data.id,
        payload: { tags: parseTags(tagsDraft) },
      });
      setMessage("已保存文章标签。");
      await article.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存文章标签失败");
    }
  }

  async function handleToggleFavorite() {
    try {
      await mutations.updateArticle.mutateAsync({
        articleId: data.id,
        payload: { is_favorited: !data.is_favorited },
      });
      setMessage(data.is_favorited ? "已取消收藏。" : "已加入收藏。");
      await article.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "更新收藏状态失败");
    }
  }

  async function handleAnalyze() {
    try {
      await mutations.analyzeArticle.mutateAsync(data.id);
      setMessage("已完成这篇文章的 LLM 总结。");
      await article.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "执行 LLM 总结失败");
    }
  }

  return (
    <PageFrame
      title="文章详情"
      subtitle="在这里查看全文、管理标签，并按需重新生成摘要。"
      actions={
        <>
          <Link href="/articles">
            <ActionButton variant="ghost">
              <ArrowLeft size={14} className="mr-2" />
              返回文章浏览
            </ActionButton>
          </Link>
          <ActionButton variant={data.is_favorited ? "solid" : "ghost"} onClick={handleToggleFavorite}>
            <Star size={14} className={`mr-2 ${data.is_favorited ? "fill-current" : ""}`} />
            {data.is_favorited ? "取消收藏" : "加入收藏"}
          </ActionButton>
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
      {message ? (
        <p className="mb-5 rounded-[18px] border border-white/10 bg-black/20 px-4 py-3 text-[13px] text-white/70">{message}</p>
      ) : null}

      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1.15fr)_380px]">
        <section className="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-sm text-white/50">{data.source?.name ?? "未知来源"}</p>
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white/70">
                  {llmStatusLabel(data.llm_summary_status)}
                </span>
                {data.is_favorited ? (
                  <span className="rounded-full border border-[#ffd478]/25 bg-[#ffd478]/10 px-3 py-1 text-xs text-[#ffe0a2]">
                    已收藏
                  </span>
                ) : null}
              </div>

              <h3 className="mt-3 text-3xl font-semibold leading-tight text-white lg:text-[2.2rem]">{data.title}</h3>

              <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-[13px] text-white/52">
                <span>作者：{data.author ?? "未知"}</span>
                <span>发布时间：{data.publish_time ?? "未知"}</span>
                <span>最近总结：{formatDateTimeShanghai(data.llm_summary_updated_at)}</span>
              </div>

              {data.all_tags.length ? (
                <div className="mt-5">
                  <TagPills items={data.all_tags} />
                </div>
              ) : null}
            </div>

            <div className="grid gap-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-[18px] border border-white/10 bg-black/20 p-3.5">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-white/36">Tags</p>
                  <p className="mt-2 text-2xl font-semibold text-white">{data.all_tags.length}</p>
                  <p className="mt-1 text-xs text-white/45">当前生效标签数</p>
                </div>
                <div className="rounded-[18px] border border-white/10 bg-black/20 p-3.5">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-white/36">Source</p>
                  <p className="mt-2 text-sm font-medium text-white">{data.source?.source_group ?? "未分组"}</p>
                  <p className="mt-1 text-xs text-white/45">来源分组</p>
                </div>
              </div>

              <div className="rounded-[18px] border border-white/10 bg-white/5 p-3.5">
                <p className="text-[11px] uppercase tracking-[0.2em] text-white/36">Links</p>
                <div className="mt-3 space-y-3">
                  <a
                    href={originalUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-between rounded-[16px] border border-white/10 bg-black/20 px-3 py-3 text-[13px] text-white/74 transition hover:border-white/20 hover:bg-black/30"
                  >
                    <span>查看原文</span>
                    <ExternalLink size={14} />
                  </a>
                  {homeLink ? (
                    <a
                      href={homeLink}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between rounded-[16px] border border-white/10 bg-black/20 px-3 py-3 text-[13px] text-white/74 transition hover:border-white/20 hover:bg-black/30"
                    >
                      <span>打开公众号主页</span>
                      <ExternalLink size={14} />
                    </a>
                  ) : (
                    <div className="rounded-[16px] border border-white/10 bg-black/20 px-3 py-3 text-[13px] text-white/48">
                      未提取到主页链接
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="space-y-6">
          <section className="rounded-[24px] border border-white/10 bg-white/5 p-4">
            <SectionTitle title="AI 摘要" subtitle="需要时可单独生成或重新生成，不影响原始文章内容。" />
            <div className="space-y-4 text-sm text-white/70">
              <div className="grid gap-3 rounded-[18px] border border-white/10 bg-black/20 p-3.5">
                <p>当前状态：{llmStatusLabel(data.llm_summary_status)}</p>
                <p>最近总结时间：{formatDateTimeShanghai(data.llm_summary_updated_at)}</p>
                <p>最近错误：{data.llm_summary_error ?? "--"}</p>
              </div>
              <ActionButton variant="solid" onClick={handleAnalyze} disabled={mutations.analyzeArticle.isPending}>
                <Sparkles size={14} className="mr-2" />
                {mutations.analyzeArticle.isPending
                  ? "总结中..."
                  : data.llm_summary_status === "completed"
                    ? "重新执行 LLM 总结"
                    : "执行 LLM 总结"}
              </ActionButton>
            </div>
          </section>

          <section className="rounded-[24px] border border-white/10 bg-white/5 p-4">
            <SectionTitle title="标签管理" subtitle="你可以在这里补充、删减或修正文章标签。" />
            <div className="space-y-4">
              <div>
                <Label>文章标签</Label>
                <Input value={tagsDraft} onChange={(event) => setTagsDraft(event.target.value)} placeholder="多个标签用逗号分隔" />
              </div>
              <ActionButton variant="solid" onClick={handleSave} disabled={mutations.updateArticle.isPending}>
                <Save size={14} className="mr-2" />
                保存标签
              </ActionButton>
            </div>
          </section>
        </div>
      </div>

      {data.summary ? (
        <section className="mt-6 rounded-[24px] border border-white/10 bg-white/5 p-5">
          <SectionTitle title="摘要" subtitle="完整展示当前摘要内容。" />
          <div className="rounded-[20px] border border-white/10 bg-black/20 px-5 py-5 sm:px-6">
            <div className="space-y-4">
              {summaryParagraphs.map((paragraph, index) => (
                <p
                  key={index}
                  className="whitespace-pre-wrap break-words text-[15px] leading-8 text-white/76 lg:text-[16px] lg:leading-9"
                >
                  {paragraph}
                </p>
              ))}
            </div>
          </div>
        </section>
      ) : null}

        <section className="mt-6 rounded-[24px] border border-white/10 bg-white/5 p-5">
        <SectionTitle title="正文" subtitle="以阅读舒适度为优先，适配笔记本与大屏显示。" />
        <div className="rounded-[22px] border border-white/10 bg-[#0b1220]/80 px-5 py-6 sm:px-7 lg:px-10">
          {paragraphs.length ? (
            <div className="mx-auto max-w-[84ch] space-y-6">
              {paragraphs.map((paragraph, index) => (
                <p key={index} className="text-[15px] leading-8 text-white/78 lg:text-[16px] lg:leading-9">
                  {paragraph}
                </p>
              ))}
            </div>
          ) : (
            <p className="text-sm text-white/60">暂无正文文本</p>
          )}
        </div>
      </section>
    </PageFrame>
  );
}

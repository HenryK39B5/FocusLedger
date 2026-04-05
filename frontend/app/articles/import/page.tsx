"use client";

import Link from "next/link";
import { ArrowRight, Link2, Upload } from "lucide-react";
import { useMemo, useState } from "react";
import { ActionButton, EmptyState, PageFrame, SectionTitle, Textarea } from "@/components/ui";
import { useMutations } from "@/lib/queries";
import type { ArticleImportResult } from "@/lib/types";

function parseUrls(value: string) {
  return value
    .split(/[\n\r,，\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item, index, list) => list.indexOf(item) === index);
}

function statusTone(status: string) {
  switch (status) {
    case "imported":
      return "border-emerald-400/30 bg-emerald-500/10 text-emerald-100";
    case "updated":
      return "border-sky-400/30 bg-sky-500/10 text-sky-100";
    default:
      return "border-red-400/30 bg-red-500/10 text-red-100";
  }
}

function statusLabel(status: string) {
  switch (status) {
    case "imported":
      return "新导入";
    case "updated":
      return "已更新";
    default:
      return "失败";
  }
}

export default function ArticleImportPage() {
  const mutations = useMutations();
  const [input, setInput] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ArticleImportResult | null>(null);

  const urls = useMemo(() => parseUrls(input), [input]);

  async function handleImport() {
    if (!urls.length) {
      setMessage("请先粘贴一篇或多篇公众号文章链接。");
      return;
    }

    setMessage("");
    try {
      const next = await mutations.importArticleLinks.mutateAsync(urls);
      setResult(next);
      setMessage(
        `本次共处理 ${next.total} 篇链接，导入 ${next.imported_count} 篇，更新 ${next.updated_count} 篇，失败 ${next.failed_count} 篇，新建来源 ${next.source_created_count} 个。`,
      );
    } catch (error) {
      setResult(null);
      setMessage(error instanceof Error ? error.message : "链接导入失败。");
    }
  }

  return (
    <PageFrame
      title="文章链接导入"
      subtitle="直接粘贴单篇或多篇公众号文章链接，系统会抓取正文入库；若对应来源不存在，会自动创建一个未绑定凭据的来源。"
      actions={
        <>
          <Link href="/articles">
            <ActionButton variant="ghost">文章浏览</ActionButton>
          </Link>
          <Link href="/sources">
            <ActionButton variant="ghost">来源管理</ActionButton>
          </Link>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle
            title="粘贴链接"
            subtitle="支持换行、空格或逗号分隔。当前仅面向公众号文章链接。"
          />
          <div className="space-y-4">
            <Textarea
              className="min-h-[240px]"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={`https://mp.weixin.qq.com/s/...\nhttps://mp.weixin.qq.com/s/...`}
            />
            <div className="flex flex-wrap items-center gap-3">
              <ActionButton variant="solid" onClick={handleImport} disabled={mutations.importArticleLinks.isPending}>
                <Upload size={14} className="mr-2" />
                {mutations.importArticleLinks.isPending ? "导入中..." : "开始导入"}
              </ActionButton>
              <p className="text-sm text-white/50">已识别 {urls.length} 篇唯一链接</p>
            </div>
            {message ? (
              <p className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm leading-6 text-white/75">
                {message}
              </p>
            ) : null}
          </div>
        </section>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle
            title="导入结果"
            subtitle="这里展示每篇链接的处理状态、落库文章和自动创建的来源。后续 QClaw skill 会复用这条链路。"
          />
          {!result?.items.length ? (
            <EmptyState
              title="还没有导入结果"
              description="完成一次导入后，这里会列出每篇链接的处理结果，并给出文章和来源的落库情况。"
            />
          ) : (
            <div className="space-y-3">
              {result.items.map((item, index) => (
                <div key={`${item.input_url}-${index}`} className="rounded-[22px] border border-white/10 bg-black/20 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full border px-2.5 py-1 text-xs ${statusTone(item.status)}`}>
                      {statusLabel(item.status)}
                    </span>
                    {item.source_created ? (
                      <span className="rounded-full border border-amber-400/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-100">
                        已自动创建来源
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-3 grid gap-2 text-sm leading-6 text-white/75">
                    <p className="break-all text-white/55">输入链接：{item.input_url}</p>
                    {item.normalized_url ? <p className="break-all text-white/55">规范链接：{item.normalized_url}</p> : null}
                    <p>结果：{item.message}</p>
                    {item.article_title ? <p className="text-white">文章：{item.article_title}</p> : null}
                    {item.source_name ? <p>来源：{item.source_name}</p> : null}
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {item.article_id ? (
                      <Link href={`/articles/${item.article_id}`}>
                        <ActionButton variant="ghost">
                          查看文章
                          <ArrowRight size={14} className="ml-2" />
                        </ActionButton>
                      </Link>
                    ) : null}
                    {item.normalized_url ? (
                      <a href={item.normalized_url} target="_blank" rel="noreferrer">
                        <ActionButton variant="ghost">
                          打开原文
                          <Link2 size={14} className="ml-2" />
                        </ActionButton>
                      </a>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </PageFrame>
  );
}

"use client";

import Link from "next/link";
import { ClipboardCopy, ExternalLink, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useMutations, useSources } from "@/lib/queries";
import type { WechatHomeLinkResolveResult } from "@/lib/types";
import { summarizeWechatSourceIdentifier } from "@/lib/wechat";
import { ActionButton, EmptyState, Input, Label, PageFrame, SectionTitle, TagPills, Textarea } from "@/components/ui";

type SourceSyncSettings = {
  pageStart: number;
  pageEnd: number;
  sinceDays: string;
};

const defaultSyncSettings: SourceSyncSettings = {
  pageStart: 1,
  pageEnd: 20,
  sinceDays: "7",
};

function parseSinceDays(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return Math.floor(parsed);
}

function clampPage(value: number) {
  if (!Number.isFinite(value) || value < 1) {
    return 1;
  }
  return Math.floor(value);
}

function normalizeGroupPath(path?: string | null) {
  if (!path) {
    return "";
  }
  return path
    .split(/[\\/]+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .join("/");
}

function parseTags(value: string) {
  return value
    .split(/[,\n，]+/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .filter((tag, index, list) => list.indexOf(tag) === index);
}

export default function CollectPage() {
  const sources = useSources();
  const mutations = useMutations();

  const [articleUrl, setArticleUrl] = useState("");
  const [resolveResult, setResolveResult] = useState<WechatHomeLinkResolveResult | null>(null);
  const [resolveMessage, setResolveMessage] = useState("");
  const [resolveLoading, setResolveLoading] = useState(false);

  const [sourceName, setSourceName] = useState("");
  const [sourceIdentifier, setSourceIdentifier] = useState("");
  const [sourceGroup, setSourceGroup] = useState("");
  const [sourceTags, setSourceTags] = useState("");
  const [sourceDescription, setSourceDescription] = useState("");
  const [formMessage, setFormMessage] = useState("");

  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [syncMessage, setSyncMessage] = useState("");
  const [sourceSyncSettings, setSourceSyncSettings] = useState<Record<string, SourceSyncSettings>>({});

  const sourceRows = useMemo(() => sources.data ?? [], [sources.data]);

  function getSourceSettings(sourceId: string) {
    return sourceSyncSettings[sourceId] ?? defaultSyncSettings;
  }

  function updateSourceSettings(sourceId: string, patch: Partial<SourceSyncSettings>) {
    setSourceSyncSettings((current) => ({
      ...current,
      [sourceId]: {
        ...defaultSyncSettings,
        ...current[sourceId],
        ...patch,
      },
    }));
  }

  async function handleResolveHome() {
    const value = articleUrl.trim();
    if (!value) {
      setResolveMessage("请先输入一篇公众号文章链接。");
      return;
    }

    setResolveLoading(true);
    setResolveMessage("");
    try {
      const result = await mutations.resolveWechatHome.mutateAsync(value);
      setResolveResult(result);
      setResolveMessage(result.message ?? "主页链接解析完成。");
      if (result.source_name && !sourceName) {
        setSourceName(result.source_name);
      }
      if (result.public_home_link) {
        setSourceDescription("公众号主页已解析，可复制到微信 PC 的文件传输助手里打开。");
      }
    } catch (error) {
      setResolveResult(null);
      setResolveMessage(error instanceof Error ? error.message : "主页链接解析失败。");
    } finally {
      setResolveLoading(false);
    }
  }

  async function handleCreateSource() {
    setFormMessage("");

    if (!sourceName.trim() || !sourceIdentifier.trim()) {
      setFormMessage("请填写来源名称和 Fiddler 抓到的 profile_ext 链接。");
      return;
    }

    if (!sourceIdentifier.includes("profile_ext")) {
      setFormMessage("这里需要粘贴 profile_ext 链接，优先使用 action=report。");
      return;
    }

    if (sourceIdentifier.includes("action=urlcheck") && !sourceIdentifier.includes("__biz=")) {
      setFormMessage("urlcheck 通常只是预检链接，优先改用 action=report 那条。");
      return;
    }

    try {
      await mutations.createSource.mutateAsync({
        name: sourceName.trim(),
        source_type: "wechat_public_account",
        source_identifier: sourceIdentifier.trim(),
        source_group: normalizeGroupPath(sourceGroup) || null,
        tags: parseTags(sourceTags),
        description: sourceDescription.trim() || null,
      });
      setFormMessage("来源已创建，现在可以直接同步。");
      setSourceIdentifier("");
      setSourceGroup("");
      setSourceTags("");
      setSourceDescription("");
      await sources.refetch();
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "创建来源失败。");
    }
  }

  async function handleSyncSource(sourceId: string) {
    const settings = getSourceSettings(sourceId);
    const sinceDays = parseSinceDays(settings.sinceDays);
    const currentSource = sourceRows.find((item) => item.id === sourceId);
    setSyncingId(sourceId);
    setSyncMessage(
      `正在同步《${currentSource?.name ?? "该来源"}》，页码 ${clampPage(settings.pageStart)}-${clampPage(settings.pageEnd)}${
        sinceDays ? `，近 ${sinceDays} 天` : "，不限天数"
      }。`,
    );
    try {
      const result = await mutations.runIngestion.mutateAsync({
        sourceId,
        pageStart: clampPage(settings.pageStart),
        pageEnd: clampPage(settings.pageEnd),
        sinceDays,
      });
      setSyncMessage(result.message || `同步完成：新增 ${result.imported_count} 篇，更新 ${result.updated_count} 篇。`);
      await sources.refetch();
    } catch (error) {
      setSyncMessage(error instanceof Error ? error.message : "同步失败。");
    } finally {
      setSyncingId(null);
    }
  }

  async function handleDelete(sourceId: string, sourceNameValue: string) {
    if (!window.confirm(`确认删除来源《${sourceNameValue}》吗？该来源下的文章也会一起删除。`)) {
      return;
    }
    await mutations.deleteSource.mutateAsync(sourceId);
  }

  async function handleCopy(text?: string | null) {
    if (!text) {
      return;
    }
    await navigator.clipboard.writeText(text);
    setResolveMessage("已复制到剪贴板。");
  }

  return (
    <PageFrame
      title="公众号采集"
      subtitle="先解析公众号主页，再在微信 PC 和 Fiddler 中拿到 profile_ext 链接，最后创建来源并执行同步。"
      actions={
        <>
          <Link href="/sources">
            <ActionButton variant="ghost">前往来源管理</ActionButton>
          </Link>
          <Link href="/articles">
            <ActionButton variant="ghost">前往文章浏览</ActionButton>
          </Link>
          <ActionButton variant="ghost" onClick={() => sources.refetch()}>
            <RefreshCw size={14} className="mr-2" />
            刷新
          </ActionButton>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle title="第一步：提取公众号主页" subtitle="输入任意一篇真实公众号文章链接，先解析它所属公众号的主页。" />
          <div className="space-y-4">
            <div>
              <Label>文章链接</Label>
              <Input
                value={articleUrl}
                onChange={(event) => setArticleUrl(event.target.value)}
                placeholder="https://mp.weixin.qq.com/s/..."
              />
            </div>
            <div className="flex flex-wrap gap-3">
              <ActionButton variant="solid" onClick={handleResolveHome} disabled={resolveLoading}>
                <ClipboardCopy size={14} className="mr-2" />
                {resolveLoading ? "解析中..." : "提取主页链接"}
              </ActionButton>
              <ActionButton
                variant="ghost"
                onClick={() => handleCopy(resolveResult?.public_home_link)}
                disabled={!resolveResult?.public_home_link}
              >
                <ExternalLink size={14} className="mr-2" />
                复制主页链接
              </ActionButton>
            </div>
            {resolveMessage ? (
              <p className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white/70">{resolveMessage}</p>
            ) : null}
            {resolveResult ? (
              <div className="rounded-[24px] border border-white/10 bg-black/20 p-4">
                <div className="grid gap-3 text-sm text-white/70">
                  <div>
                    <p className="text-white/50">公众号名称</p>
                    <p className="mt-1 text-white">{resolveResult.source_name || "未识别"}</p>
                  </div>
                  <div>
                    <p className="text-white/50">主页链接</p>
                    <p className="mt-1 break-all text-white">{resolveResult.public_home_link || "未提取到"}</p>
                  </div>
                  <div>
                    <p className="text-white/50">下一步</p>
                    <p className="mt-1 leading-6 text-white/65">
                      把这个主页链接发到微信 PC 的文件传输助手里打开，再用 Fiddler 复制一条
                      <code className="mx-1 rounded bg-white/10 px-1.5 py-0.5 text-xs">profile_ext</code>
                      请求。优先使用
                      <code className="mx-1 rounded bg-white/10 px-1.5 py-0.5 text-xs">action=report</code>
                      那条完整链接。
                    </p>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </section>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle title="第二步：创建采集来源" subtitle="把 Fiddler 复制出来的 profile_ext 链接保存成来源，后续同步可以重复使用。" />
          <div className="space-y-4">
            <div>
              <Label>来源名称</Label>
              <Input value={sourceName} onChange={(event) => setSourceName(event.target.value)} placeholder="例如：新智元" />
            </div>
            <div>
              <Label>Fiddler 链接</Label>
              <Textarea
                value={sourceIdentifier}
                onChange={(event) => setSourceIdentifier(event.target.value)}
                placeholder="https://mp.weixin.qq.com/mp/profile_ext?action=report&..."
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label>分组路径</Label>
                <Input value={sourceGroup} onChange={(event) => setSourceGroup(event.target.value)} placeholder="例如：投研/科技" />
              </div>
              <div>
                <Label>标签</Label>
                <Input value={sourceTags} onChange={(event) => setSourceTags(event.target.value)} placeholder="例如：AI, 商业, 出海" />
              </div>
            </div>
            <div>
              <Label>备注</Label>
              <Textarea
                value={sourceDescription}
                onChange={(event) => setSourceDescription(event.target.value)}
                placeholder="记录这个公众号为什么值得跟踪"
              />
            </div>
            <ActionButton variant="solid" onClick={handleCreateSource} disabled={mutations.createSource.isPending}>
              <Plus size={14} className="mr-2" />
              创建来源
            </ActionButton>
            {formMessage ? <p className="text-sm text-white/70">{formMessage}</p> : null}
          </div>
        </section>
      </div>

      <section className="mt-8 rounded-[28px] border border-white/10 bg-white/5 p-5">
        <SectionTitle title="第三步：同步来源" subtitle="每个来源都可以单独设置页码和时间范围，再发起同步。" />
        {syncMessage ? <p className="mb-4 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white/70">{syncMessage}</p> : null}
        {!sourceRows.length ? (
          <EmptyState title="暂无来源" description="先完成上面的创建流程，再回来执行同步。" />
        ) : (
          <div className="grid gap-4">
            {sourceRows.map((source) => {
              const settings = getSourceSettings(source.id);
              return (
                <div key={source.id} className="rounded-[24px] border border-white/10 bg-black/20 p-5">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <h4 className="text-lg text-white">{source.name}</h4>
                      <p className="mt-2 text-sm text-white/50">{summarizeWechatSourceIdentifier(source.source_identifier)}</p>
                      {source.source_group ? <p className="mt-2 text-sm text-white/60">分组：{source.source_group}</p> : null}
                      {source.tags.length ? (
                        <div className="mt-3">
                          <TagPills items={source.tags} />
                        </div>
                      ) : null}
                    </div>
                    <div className="flex gap-2">
                      <ActionButton
                        variant="solid"
                        onClick={() => handleSyncSource(source.id)}
                        disabled={syncingId === source.id || mutations.runIngestion.isPending}
                      >
                        <RefreshCw size={14} className="mr-2" />
                        {syncingId === source.id ? "同步中..." : "同步此来源"}
                      </ActionButton>
                      <ActionButton variant="danger" onClick={() => handleDelete(source.id, source.name)}>
                        <Trash2 size={14} className="mr-2" />
                        删除
                      </ActionButton>
                    </div>
                  </div>

                  <div className="mt-5 grid gap-4 md:grid-cols-3">
                    <div>
                      <Label>起始页</Label>
                      <Input
                        type="number"
                        min={1}
                        value={settings.pageStart}
                        onChange={(event) => updateSourceSettings(source.id, { pageStart: Number(event.target.value) || 1 })}
                      />
                    </div>
                    <div>
                      <Label>结束页</Label>
                      <Input
                        type="number"
                        min={1}
                        value={settings.pageEnd}
                        onChange={(event) => updateSourceSettings(source.id, { pageEnd: Number(event.target.value) || 1 })}
                      />
                    </div>
                    <div>
                      <Label>近几天</Label>
                      <Input
                        value={settings.sinceDays}
                        onChange={(event) => updateSourceSettings(source.id, { sinceDays: event.target.value })}
                        placeholder="留空表示不限天数"
                      />
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <ActionButton variant="ghost" onClick={() => updateSourceSettings(source.id, { sinceDays: "7" })}>
                      近 7 天
                    </ActionButton>
                    <ActionButton variant="ghost" onClick={() => updateSourceSettings(source.id, { sinceDays: "30" })}>
                      近 30 天
                    </ActionButton>
                    <ActionButton variant="ghost" onClick={() => updateSourceSettings(source.id, { sinceDays: "" })}>
                      不限天数
                    </ActionButton>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </PageFrame>
  );
}

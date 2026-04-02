"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { PencilLine, Save, Sparkles, Trash2, X } from "lucide-react";
import { useMutations, useSources } from "@/lib/queries";
import type { ArticleSource } from "@/lib/types";
import { credentialStatusLabel, formatDateTimeShanghai, summarizeWechatHomeLink } from "@/lib/wechat";
import { ActionButton, EmptyState, Input, Label, PageFrame, TagPills, Textarea } from "@/components/ui";

type SourceDraft = {
  name: string;
  source_group: string;
  tags: string;
  description: string;
};

const GROUP_ALL = "__all__";
const GROUP_UNGROUPED = "__ungrouped__";

function normalizeGroupPath(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  return value
    .split(/[\\/]+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .join("/");
}

function parseTags(value: string) {
  return value
    .split(/[,\n，]/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .filter((tag, index, list) => list.indexOf(tag) === index);
}

function formatTags(tags: string[]) {
  return tags.join(", ");
}

function statusTone(status: string) {
  switch (status) {
    case "valid":
      return "border-emerald-400/25 bg-emerald-500/10 text-emerald-100";
    case "refresh_required":
      return "border-amber-400/25 bg-amber-500/10 text-amber-100";
    case "invalid":
      return "border-red-400/25 bg-red-500/10 text-red-100";
    default:
      return "border-white/10 bg-white/5 text-white/68";
  }
}

function buildGroupOptions(sources: ArticleSource[]) {
  const groups = new Set<string>();
  for (const source of sources) {
    const path = normalizeGroupPath(source.source_group);
    if (path) {
      groups.add(path);
    }
  }
  return Array.from(groups).sort((left, right) => left.localeCompare(right, "zh-Hans-CN"));
}

function filterSources(sources: ArticleSource[], selectedGroup: string) {
  if (selectedGroup === GROUP_ALL) {
    return sources;
  }
  if (selectedGroup === GROUP_UNGROUPED) {
    return sources.filter((source) => !normalizeGroupPath(source.source_group));
  }
  return sources.filter((source) => normalizeGroupPath(source.source_group) === selectedGroup);
}

export default function SourcesPage() {
  const sources = useSources();
  const mutations = useMutations();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDrafts, setEditDrafts] = useState<Record<string, SourceDraft>>({});
  const [selectedGroup, setSelectedGroup] = useState<string>(GROUP_ALL);
  const [message, setMessage] = useState("");

  const sourceItems = sources.data ?? [];
  const groupOptions = useMemo(() => buildGroupOptions(sourceItems), [sourceItems]);
  const visibleSources = useMemo(
    () => filterSources(sourceItems, selectedGroup).sort((left, right) => right.updated_at.localeCompare(left.updated_at)),
    [selectedGroup, sourceItems],
  );

  function startEdit(source: ArticleSource) {
    setEditingId(source.id);
    setEditDrafts((current) => ({
      ...current,
      [source.id]: {
        name: source.name,
        source_group: source.source_group ?? "",
        tags: formatTags(source.tags ?? []),
        description: source.description ?? "",
      },
    }));
  }

  function updateDraft(sourceId: string, patch: Partial<SourceDraft>) {
    const currentDraft = editDrafts[sourceId] ?? {
      name: "",
      source_group: "",
      tags: "",
      description: "",
    };
    setEditDrafts((current) => ({
      ...current,
      [sourceId]: {
        ...currentDraft,
        ...patch,
      },
    }));
  }

  async function handleSave(source: ArticleSource) {
    const draft = editDrafts[source.id];
    if (!draft) {
      return;
    }

    try {
      await mutations.updateSource.mutateAsync({
        sourceId: source.id,
        payload: {
          name: draft.name.trim(),
          source_group: normalizeGroupPath(draft.source_group) || null,
          tags: parseTags(draft.tags),
          description: draft.description.trim() || null,
        },
      });
      setEditingId(null);
      setMessage(`已更新来源《${source.name}》。`);
      await sources.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "更新来源失败");
    }
  }

  async function handleDelete(source: ArticleSource) {
    if (!window.confirm(`确认删除来源《${source.name}》吗？该来源下的文章也会一起删除。`)) {
      return;
    }
    try {
      await mutations.deleteSource.mutateAsync(source.id);
      setMessage(`已删除来源《${source.name}》。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "删除来源失败");
    }
  }

  async function handleAnalyzeOne(source: ArticleSource) {
    try {
      await mutations.analyzeSource.mutateAsync(source.id);
      setMessage(`已完成《${source.name}》的 AI 分组与打标签。`);
      await sources.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "AI 分组与打标签失败");
    }
  }

  async function handleAnalyzeVisible() {
    if (!visibleSources.length) {
      return;
    }
    try {
      const result = await mutations.batchAnalyzeSources.mutateAsync(visibleSources.map((source) => source.id));
      setMessage(`本次 AI 处理完成：成功 ${result.analyzed_count} 个，失败 ${result.failed_ids.length} 个。`);
      await sources.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "批量 AI 分组与打标签失败");
    }
  }

  function renderSourceCard(source: ArticleSource) {
    const isEditing = editingId === source.id;
    const draft = editDrafts[source.id];

    if (isEditing && draft) {
      return (
        <div key={source.id} className="rounded-[24px] border border-white/10 bg-black/20 p-5">
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <Label>名称</Label>
              <Input value={draft.name} onChange={(event) => updateDraft(source.id, { name: event.target.value })} />
            </div>
            <div>
              <Label>分组路径</Label>
              <Input
                value={draft.source_group}
                onChange={(event) => updateDraft(source.id, { source_group: event.target.value })}
                placeholder="例如：研究/卖方/宏观"
              />
            </div>
            <div className="lg:col-span-2">
              <Label>标签</Label>
              <Input
                value={draft.tags}
                onChange={(event) => updateDraft(source.id, { tags: event.target.value })}
                placeholder="多个标签用逗号分隔"
              />
            </div>
            <div className="lg:col-span-2">
              <Label>备注</Label>
              <Textarea value={draft.description} onChange={(event) => updateDraft(source.id, { description: event.target.value })} />
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <ActionButton variant="solid" onClick={() => handleSave(source)} disabled={mutations.updateSource.isPending}>
              <Save size={14} className="mr-2" />
              保存
            </ActionButton>
            <ActionButton variant="ghost" onClick={() => setEditingId(null)}>
              <X size={14} className="mr-2" />
              取消
            </ActionButton>
          </div>
        </div>
      );
    }

    return (
      <div key={source.id} className="rounded-[24px] border border-white/10 bg-black/20 px-5 py-4">
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.9fr)] xl:items-start">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-base font-medium text-white">{source.name}</h4>
              <span className={`rounded-full border px-2.5 py-1 text-[11px] ${statusTone(source.credential_status)}`}>
                {credentialStatusLabel(source.credential_status)}
              </span>
              {source.source_group ? (
                <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-white/55">
                  {source.source_group}
                </span>
              ) : null}
            </div>

            <p className="mt-2 text-sm text-white/48">{summarizeWechatHomeLink(source.public_home_link, source.biz)}</p>
            {source.description ? <p className="mt-3 text-sm leading-6 text-white/62">{source.description}</p> : null}

            {source.tags.length ? (
              <div className="mt-3">
                <TagPills items={source.tags} />
              </div>
            ) : null}
          </div>

          <div className="grid gap-3 rounded-[20px] border border-white/10 bg-white/5 p-4">
            <div className="grid grid-cols-2 gap-3 text-xs text-white/48">
              <div>
                <div className="text-white/34">最后验证</div>
                <div className="mt-1 text-sm text-white/72">{formatDateTimeShanghai(source.last_verified_at)}</div>
              </div>
              <div>
                <div className="text-white/34">最后成功同步</div>
                <div className="mt-1 text-sm text-white/72">{formatDateTimeShanghai(source.last_sync_succeeded_at)}</div>
              </div>
            </div>
            <div className="text-xs text-white/44">最近错误</div>
            <div className="text-sm leading-6 text-white/65">{source.last_error_message ?? "--"}</div>
            <div className="flex flex-wrap gap-2 pt-1">
              <ActionButton
                variant="ghost"
                onClick={() => handleAnalyzeOne(source)}
                disabled={mutations.analyzeSource.isPending || mutations.batchAnalyzeSources.isPending}
              >
                <Sparkles size={14} className="mr-2" />
                AI 分组标签
              </ActionButton>
              <ActionButton variant="ghost" onClick={() => startEdit(source)}>
                <PencilLine size={14} className="mr-2" />
                编辑
              </ActionButton>
              <ActionButton variant="danger" onClick={() => handleDelete(source)} disabled={mutations.deleteSource.isPending}>
                <Trash2 size={14} className="mr-2" />
                删除
              </ActionButton>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <PageFrame
      title="来源管理"
      subtitle="集中维护来源分组、来源标签、凭据状态和来源说明；支持用 LLM 批量整理来源结构。"
      actions={
        <>
          <ActionButton
            variant="ghost"
            onClick={handleAnalyzeVisible}
            disabled={!visibleSources.length || mutations.batchAnalyzeSources.isPending}
          >
            <Sparkles size={14} className="mr-2" />
            AI 整理当前分组
          </ActionButton>
          <Link href="/collect">
            <ActionButton variant="ghost">前往文章获取</ActionButton>
          </Link>
          <Link href="/sources/add">
            <ActionButton variant="solid">添加来源</ActionButton>
          </Link>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-white/42">Groups</p>
            <h3 className="mt-2 text-xl font-semibold text-white">分组视图</h3>
            <p className="mt-2 text-sm leading-6 text-white/55">左侧只负责切换视角，右侧集中展示来源明细和 AI 整理动作。</p>
          </div>

          <div className="mt-5 space-y-2">
            <button
              type="button"
              onClick={() => setSelectedGroup(GROUP_ALL)}
              className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                selectedGroup === GROUP_ALL
                  ? "border-white/20 bg-white/10 text-white"
                  : "border-white/10 bg-black/20 text-white/70 hover:bg-black/30"
              }`}
            >
              全部来源
            </button>
            <button
              type="button"
              onClick={() => setSelectedGroup(GROUP_UNGROUPED)}
              className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                selectedGroup === GROUP_UNGROUPED
                  ? "border-white/20 bg-white/10 text-white"
                  : "border-white/10 bg-black/20 text-white/70 hover:bg-black/30"
              }`}
            >
              未分组
            </button>
            {groupOptions.map((group) => (
              <button
                key={group}
                type="button"
                onClick={() => setSelectedGroup(group)}
                className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                  selectedGroup === group
                    ? "border-white/20 bg-white/10 text-white"
                    : "border-white/10 bg-black/20 text-white/70 hover:bg-black/30"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate">{group}</span>
                  <span className="text-xs text-white/42">{filterSources(sourceItems, group).length}</span>
                </div>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <div className="flex flex-col gap-3 border-b border-white/10 pb-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-white/42">Sources</p>
              <h3 className="mt-2 text-xl font-semibold text-white">
                {selectedGroup === GROUP_ALL ? "全部来源" : selectedGroup === GROUP_UNGROUPED ? "未分组来源" : selectedGroup}
              </h3>
              <p className="mt-1 text-sm text-white/55">共 {visibleSources.length} 个来源</p>
            </div>
            {message ? (
              <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white/70">{message}</div>
            ) : null}
          </div>

          <div className="mt-5">
            {sources.isLoading ? (
              <EmptyState title="正在加载来源" description="请稍候，系统正在读取来源列表。" />
            ) : visibleSources.length ? (
              <div className="space-y-4">{visibleSources.map(renderSourceCard)}</div>
            ) : (
              <EmptyState title="当前视图没有来源" description="先添加真实来源，或切换到其他分组查看。" />
            )}
          </div>
        </section>
      </div>
    </PageFrame>
  );
}

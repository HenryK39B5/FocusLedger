"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { PencilLine, Save, Trash2, X } from "lucide-react";
import { useMutations, useSources } from "@/lib/queries";
import type { ArticleSource } from "@/lib/types";
import { summarizeWechatSourceIdentifier } from "@/lib/wechat";
import { ActionButton, EmptyState, Input, Label, PageFrame, SectionTitle, TagPills, Textarea } from "@/components/ui";

type SourceDraft = {
  name: string;
  source_identifier: string;
  source_group: string;
  tags: string;
  description: string;
};

type GroupNode = {
  path: string;
  name: string;
  sources: ArticleSource[];
  children: GroupNode[];
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
    .split(/[,\n，]+/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .filter((tag, index, list) => list.indexOf(tag) === index);
}

function formatTags(tags: string[]) {
  return tags.join(", ");
}

function buildGroupTree(sources: ArticleSource[]) {
  const nodes = new Map<string, GroupNode>();

  const ensureNode = (path: string): GroupNode => {
    if (!nodes.has(path)) {
      nodes.set(path, {
        path,
        name: path.split("/").at(-1) ?? path,
        sources: [],
        children: [],
      });
    }
    return nodes.get(path)!;
  };

  for (const source of sources) {
    const path = normalizeGroupPath(source.source_group);
    if (!path) {
      continue;
    }
    const parts = path.split("/");
    let cursor = "";
    for (const part of parts) {
      cursor = cursor ? `${cursor}/${part}` : part;
      ensureNode(cursor);
    }
  }

  for (const source of sources) {
    const path = normalizeGroupPath(source.source_group);
    if (!path) {
      continue;
    }
    ensureNode(path).sources.push(source);
  }

  for (const node of nodes.values()) {
    node.sources.sort((left, right) => left.name.localeCompare(right.name, "zh-Hans-CN"));
    node.children = [];
  }

  for (const node of nodes.values()) {
    const parentPath = node.path.split("/").slice(0, -1).join("/");
    if (!parentPath) {
      continue;
    }
    ensureNode(parentPath).children.push(node);
  }

  const sortNode = (node: GroupNode) => {
    node.children.sort((left, right) => left.name.localeCompare(right.name, "zh-Hans-CN"));
    node.children.forEach(sortNode);
  };

  const roots = Array.from(nodes.values()).filter((node) => !node.path.includes("/"));
  roots.sort((left, right) => left.name.localeCompare(right.name, "zh-Hans-CN"));
  roots.forEach(sortNode);

  return {
    roots,
    ungrouped: sources.filter((source) => !normalizeGroupPath(source.source_group)),
  };
}

function collectSourceCount(node: GroupNode): number {
  return node.sources.length + node.children.reduce((sum, child) => sum + collectSourceCount(child), 0);
}

export default function SourcesPage() {
  const sources = useSources();
  const mutations = useMutations();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDrafts, setEditDrafts] = useState<Record<string, SourceDraft>>({});
  const [selectedGroup, setSelectedGroup] = useState<string>(GROUP_ALL);
  const [message, setMessage] = useState("");

  const grouped = useMemo(() => buildGroupTree(sources.data ?? []), [sources.data]);

  function startEdit(source: ArticleSource) {
    setEditingId(source.id);
    setEditDrafts((current) => ({
      ...current,
      [source.id]: {
        name: source.name,
        source_identifier: source.source_identifier,
        source_group: source.source_group ?? "",
        tags: formatTags(source.tags ?? []),
        description: source.description ?? "",
      },
    }));
  }

  function updateDraft(sourceId: string, patch: Partial<SourceDraft>) {
    const currentDraft = editDrafts[sourceId] ?? {
      name: "",
      source_identifier: "",
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
          source_identifier: draft.source_identifier.trim(),
          source_group: normalizeGroupPath(draft.source_group) || null,
          tags: parseTags(draft.tags),
          description: draft.description.trim() || null,
        },
      });
      setEditingId(null);
      setMessage("来源已更新。");
      await sources.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "更新来源失败。");
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
      setMessage(error instanceof Error ? error.message : "删除来源失败。");
    }
  }

  function renderSourceCard(source: ArticleSource) {
    const isEditing = editingId === source.id;
    const draft = editDrafts[source.id];

    return (
      <div key={source.id} className="rounded-[24px] border border-white/10 bg-black/20 p-5">
        {isEditing && draft ? (
          <div className="space-y-4">
            <div>
              <Label>名称</Label>
              <Input value={draft.name} onChange={(event) => updateDraft(source.id, { name: event.target.value })} />
            </div>
            <div>
              <Label>分组路径</Label>
              <Input
                value={draft.source_group}
                onChange={(event) => updateDraft(source.id, { source_group: event.target.value })}
                placeholder="例如：投研/宏观/中国"
              />
            </div>
            <div>
              <Label>标签</Label>
              <Input
                value={draft.tags}
                onChange={(event) => updateDraft(source.id, { tags: event.target.value })}
                placeholder="多个标签用逗号分隔"
              />
            </div>
            <div>
              <Label>来源链接</Label>
              <Input
                value={draft.source_identifier}
                onChange={(event) => updateDraft(source.id, { source_identifier: event.target.value })}
              />
            </div>
            <div>
              <Label>备注</Label>
              <Textarea
                value={draft.description}
                onChange={(event) => updateDraft(source.id, { description: event.target.value })}
              />
            </div>
            <div className="flex flex-wrap gap-3">
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
        ) : (
          <div>
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h4 className="text-lg font-medium text-white">{source.name}</h4>
                <p className="mt-2 text-sm text-white/50">{summarizeWechatSourceIdentifier(source.source_identifier)}</p>
              </div>
              <div className="flex shrink-0 gap-2">
                <ActionButton variant="ghost" onClick={() => startEdit(source)}>
                  <PencilLine size={14} className="mr-2" />
                  编辑
                </ActionButton>
                <ActionButton variant="danger" onClick={() => handleDelete(source)}>
                  <Trash2 size={14} className="mr-2" />
                  删除
                </ActionButton>
              </div>
            </div>
            {source.description ? <p className="mt-4 text-sm leading-6 text-white/65">{source.description}</p> : null}
            {source.tags.length ? (
              <div className="mt-4">
                <TagPills items={source.tags} />
              </div>
            ) : null}
          </div>
        )}
      </div>
    );
  }

  function renderGroup(node: GroupNode, depth = 0): ReactNode {
    return (
      <div key={node.path} className={depth ? "mt-4" : ""}>
        <div className="rounded-[26px] border border-white/10 bg-white/4 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.25em] text-white/40">{node.path}</p>
              <h4 className="mt-2 text-xl text-white">{node.name}</h4>
              <p className="mt-2 text-sm text-white/55">本分组及其子分组共 {collectSourceCount(node)} 个公众号来源。</p>
            </div>
          </div>
          {node.sources.length ? <div className="mt-5 grid gap-4">{node.sources.map(renderSourceCard)}</div> : null}
          {node.children.length ? <div className="mt-5">{node.children.map((child) => renderGroup(child, depth + 1))}</div> : null}
        </div>
      </div>
    );
  }

  const selectedNode = useMemo(() => {
    const walk = (nodes: GroupNode[]): GroupNode | null => {
      for (const node of nodes) {
        if (node.path === selectedGroup) {
          return node;
        }
        const found = walk(node.children);
        if (found) {
          return found;
        }
      }
      return null;
    };
    if (selectedGroup === GROUP_ALL || selectedGroup === GROUP_UNGROUPED) {
      return null;
    }
    return walk(grouped.roots);
  }, [grouped.roots, selectedGroup]);

  return (
    <PageFrame
      title="来源管理"
      subtitle="这里专门管理公众号来源的分组、标签和备注。新建来源和同步行为放在采集页面。"
      actions={
        <Link href="/collect">
          <ActionButton variant="ghost">前往公众号采集</ActionButton>
        </Link>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[0.78fr_1.22fr]">
        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle title="分组目录" subtitle="一个公众号只属于一个分组，分组支持多级路径。" />
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setSelectedGroup(GROUP_ALL)}
              className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                selectedGroup === GROUP_ALL
                  ? "border-white/20 bg-white/10 text-white"
                  : "border-white/10 bg-black/20 text-white/70 hover:bg-black/30"
              }`}
            >
              全部分组
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
            {grouped.roots.map((node) => (
              <div key={node.path}>
                <button
                  type="button"
                  onClick={() => setSelectedGroup(node.path)}
                  className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                    selectedGroup === node.path
                      ? "border-white/20 bg-white/10 text-white"
                      : "border-white/10 bg-black/20 text-white/70 hover:bg-black/30"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span>{node.path}</span>
                    <span className="text-xs text-white/45">{collectSourceCount(node)}</span>
                  </div>
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle
            title={selectedGroup === GROUP_ALL ? "全部来源" : selectedGroup === GROUP_UNGROUPED ? "未分组来源" : selectedNode?.path ?? "来源"}
            subtitle="卡片上只显示标签；分组通过所在位置表达。"
          />
          {message ? <p className="mb-4 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white/70">{message}</p> : null}
          {sources.isLoading ? (
            <EmptyState title="正在加载来源" description="后端正在返回公众号来源列表。" />
          ) : selectedGroup === GROUP_ALL ? (
            grouped.roots.length || grouped.ungrouped.length ? (
              <div className="space-y-5">
                {grouped.ungrouped.length ? (
                  <div className="rounded-[26px] border border-white/10 bg-white/4 p-5">
                    <h4 className="text-xl text-white">未分组</h4>
                    <div className="mt-5 grid gap-4">{grouped.ungrouped.map(renderSourceCard)}</div>
                  </div>
                ) : null}
                {grouped.roots.map((node) => renderGroup(node))}
              </div>
            ) : (
              <EmptyState title="暂无来源" description="先去采集页面添加公众号来源，再回来整理分组和标签。" />
            )
          ) : selectedGroup === GROUP_UNGROUPED ? (
            grouped.ungrouped.length ? (
              <div className="grid gap-4">{grouped.ungrouped.map(renderSourceCard)}</div>
            ) : (
              <EmptyState title="没有未分组来源" description="当前所有来源都已经放进了某个分组。" />
            )
          ) : selectedNode ? (
            renderGroup(selectedNode)
          ) : (
            <EmptyState title="未找到分组" description="这个分组可能已经被移动或删除，请重新选择。" />
          )}
        </section>
      </div>
    </PageFrame>
  );
}

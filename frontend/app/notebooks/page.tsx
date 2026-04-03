"use client";

import Link from "next/link";
import { ChevronDown, ChevronUp, NotebookPen, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { ActionButton, EmojiPicker, EmptyState, Input, PageFrame, Textarea } from "@/components/ui";
import { useMutations, useNotebooks } from "@/lib/queries";

const EMOJI_PRESETS = ["📒", "🧠", "🛰️", "📈", "📰", "🎧", "🧾", "🧪"];

export default function NotebooksPage() {
  const notebooks = useNotebooks();
  const mutations = useMutations();

  const [name, setName] = useState("");
  const [emoji, setEmoji] = useState("📒");
  const [description, setDescription] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const items = notebooks.data?.items ?? [];
  const totalArticles = useMemo(() => items.reduce((sum, item) => sum + item.article_count, 0), [items]);

  async function handleCreateNotebook() {
    if (!name.trim()) {
      window.alert("请先填写 Notebook 名称。");
      return;
    }
    await mutations.createNotebook.mutateAsync({
      name: name.trim(),
      emoji: emoji.trim() || "📒",
      description: description.trim() || undefined,
    });
    setName("");
    setEmoji("📒");
    setDescription("");
    setShowCreate(false);
  }

  async function handleDeleteNotebook(notebookId: string, notebookName: string) {
    if (!window.confirm(`确认删除 Notebook「${notebookName}」吗？其中的文章不会被删除，只会移出工作区。`)) {
      return;
    }
    await mutations.deleteNotebook.mutateAsync(notebookId);
  }

  return (
    <PageFrame
      title="Notebooks"
      subtitle="每个 Notebook 是一个研究工作区，聚合文章来源，支持 AI 对话与播客生成。"
      actions={
        <>
          <ActionButton variant="ghost" onClick={() => notebooks.refetch()}>
            刷新
          </ActionButton>
          <ActionButton
            variant="solid"
            onClick={() => setShowCreate((prev) => !prev)}
          >
            {showCreate ? (
              <>
                <ChevronUp size={14} className="mr-1.5" />
                收起
              </>
            ) : (
              <>
                <Plus size={14} className="mr-1.5" />
                新建 Notebook
              </>
            )}
          </ActionButton>
        </>
      }
    >
      {/* Inline create form */}
      {showCreate ? (
        <div className="mb-5 rounded-[22px] border border-white/12 bg-[#0c1423]/80 p-4">
          <div className="flex items-center gap-2.5 border-b border-white/8 pb-4">
            <NotebookPen size={16} className="text-[#f7c66b]" />
            <h3 className="text-sm font-semibold text-white">新建 Notebook</h3>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-[auto_1fr_1fr_auto]">
            {/* Emoji */}
            <div>
              <p className="mb-2 text-xs text-white/48">图标</p>
              <EmojiPicker value={emoji} onChange={setEmoji} presets={EMOJI_PRESETS} placeholder="例如：📒" />
            </div>

            {/* Name */}
            <div>
              <label className="mb-2 block text-xs text-white/48">名称</label>
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="例如：AI Agent 观察站"
                maxLength={80}
              />
            </div>

            {/* Description */}
            <div>
              <label className="mb-2 block text-xs text-white/48">说明（可选）</label>
              <Input
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="这个工作区的研究方向是什么？"
                maxLength={200}
              />
            </div>

            {/* Submit */}
            <div className="flex items-end">
              <ActionButton
                variant="solid"
                onClick={handleCreateNotebook}
                disabled={mutations.createNotebook.isPending}
                className="w-full"
              >
                创建
              </ActionButton>
            </div>
          </div>
        </div>
      ) : null}

      {/* Stats bar */}
      {items.length > 0 ? (
        <p className="mb-4 text-[13px] text-white/42">
          共 {items.length} 个工作区 · {totalArticles} 篇来源文章
        </p>
      ) : null}

      {/* Notebook grid */}
      {notebooks.isLoading ? (
        <EmptyState title="正在加载 Notebook" description="正在整理当前工作区列表。" />
      ) : !items.length ? (
        <EmptyState title="还没有 Notebook" description={'点击右上角"新建 Notebook"创建第一个工作区，把文章加入进去，再开始对话或生成播客。'} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((notebook) => (
            <div
              key={notebook.id}
              className="flex flex-col rounded-[22px] border border-white/10 bg-[#101827]/80 p-4 shadow-[0_12px_40px_rgba(0,0,0,0.20)]"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-2xl shrink-0">{notebook.emoji || "📒"}</span>
                  <div className="min-w-0">
                    <Link
                      href={`/notebooks/${notebook.id}`}
                      className="block truncate text-[15px] font-semibold text-white hover:text-[#ffe1a4]"
                    >
                      {notebook.name}
                    </Link>
                    <p className="mt-0.5 text-xs text-white/36">
                      {notebook.article_count} 篇
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteNotebook(notebook.id, notebook.name)}
                  disabled={mutations.deleteNotebook.isPending}
                  className="shrink-0 rounded-lg p-1.5 text-white/28 transition hover:bg-red-500/10 hover:text-red-300 disabled:opacity-40"
                >
                  <Trash2 size={14} />
                </button>
              </div>

              <p className="mt-3 line-clamp-2 flex-1 text-[13px] leading-6 text-white/50">
                {notebook.description || "暂无说明。"}
              </p>

              <div className="mt-4 flex items-center justify-between border-t border-white/8 pt-3">
                <p className="text-xs text-white/32">
                  {new Date(notebook.updated_at).toLocaleDateString("zh-CN")}
                </p>
                <Link
                  href={`/notebooks/${notebook.id}`}
                  className="inline-flex items-center rounded-full border border-white/12 bg-white/5 px-3 py-1.5 text-[12px] text-white/75 transition hover:bg-white/10 hover:text-white"
                >
                  打开
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </PageFrame>
  );
}

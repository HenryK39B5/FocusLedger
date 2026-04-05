"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, MessageSquare, Music4, Plus, Search, Trash2 } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { ActionButton, EmojiPicker, EmptyState, Input, PageFrame, SectionTitle, TagPills, Textarea } from "@/components/ui";
import {
  useArticles,
  useMutations,
  useNotebook,
  useNotebookChat,
  useNotebookPodcastAudio,
  useNotebookPodcasts,
  useSources,
} from "@/lib/queries";
import type { ArticleSummary, NotebookPodcastAudioJob, NotebookPodcastScript } from "@/lib/types";

const EMOJI_PRESETS = ["📒", "🧠", "🛰️", "📈", "📰", "🎧", "🧾", "🧪"];
const PODCAST_FORMATS = [
  { value: "brief", label: "Brief", description: "超短综述，适合快速过一遍这个 Notebook 的核心信息。" },
  { value: "explainer", label: "Explainer", description: "单人专题讲解，把主题讲清楚，结构更完整。" },
  { value: "commentary", label: "Commentary", description: "研究评论风格，强调判断、分歧和后续观察点。" },
];

const TENCENT_VOICE_PREFIX = "tencent:";

function podcastFormatLabel(value: string) {
  const matched = PODCAST_FORMATS.find((item) => item.value === value);
  return matched?.label ?? value;
}

function audioStatusLabel(value: string | null | undefined) {
  switch (value) {
    case "queued":
      return "排队中";
    case "running":
      return "生成中";
    case "succeeded":
      return "已完成";
    case "failed":
      return "失败";
    default:
      return "未生成";
  }
}

function isTencentVoiceOption(value: string) {
  return value.startsWith(TENCENT_VOICE_PREFIX);
}

export default function NotebookDetailPage() {
  const params = useParams<{ id: string }>();
  const notebookId = typeof params?.id === "string" ? params.id : "";

  const notebook = useNotebook(notebookId || null);
  const chat = useNotebookChat(notebookId || null);
  const podcasts = useNotebookPodcasts(notebookId || null);
  const sources = useSources();
  const mutations = useMutations();

  const [name, setName] = useState("");
  const [emoji, setEmoji] = useState("📒");
  const [description, setDescription] = useState("");
  const [articleQuery, setArticleQuery] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [selectedArticleIds, setSelectedArticleIds] = useState<string[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [podcastFormat, setPodcastFormat] = useState("explainer");
  const [podcastMinutes, setPodcastMinutes] = useState(5);
  const [podcastFocus, setPodcastFocus] = useState("");
  const [activePodcastId, setActivePodcastId] = useState<string | null>(null);
  const [audioVoice, setAudioVoice] = useState("zh-CN-XiaoxiaoNeural");
  const [audioRate, setAudioRate] = useState("-8%");

  const deferredQuery = useDeferredValue(articleQuery);
  const articleSearch = useArticles({
    q: deferredQuery.trim() || undefined,
    sourceId: sourceId || undefined,
    page: 1,
    pageSize: 18,
    sort: "latest",
  });

  const notebookData = notebook.data;
  const chatMessages = chat.data?.messages ?? [];
  const podcastItems = podcasts.data?.items ?? [];

  useEffect(() => {
    if (!notebookData) {
      return;
    }
    setName(notebookData.name);
    setEmoji(notebookData.emoji || "📒");
    setDescription(notebookData.description || "");
  }, [notebookData]);

  useEffect(() => {
    if (!activePodcastId && podcastItems.length) {
      setActivePodcastId(podcastItems[0].id);
      return;
    }
    if (activePodcastId && !podcastItems.some((item) => item.id === activePodcastId)) {
      setActivePodcastId(podcastItems[0]?.id ?? null);
    }
  }, [podcastItems, activePodcastId]);

  const notebookArticleIds = useMemo(
    () => new Set((notebookData?.articles ?? []).map((article) => article.id)),
    [notebookData?.articles],
  );

  const articleMap = useMemo(() => {
    const entries: Array<[string, ArticleSummary]> = (notebookData?.articles ?? []).map((article) => [article.id, article]);
    return new Map<string, ArticleSummary>(entries);
  }, [notebookData?.articles]);

  const candidateArticles = useMemo(
    () => (articleSearch.data?.items ?? []).filter((article) => !notebookArticleIds.has(article.id)),
    [articleSearch.data?.items, notebookArticleIds],
  );

  const activePodcast: NotebookPodcastScript | null = useMemo(
    () => podcastItems.find((item) => item.id === activePodcastId) ?? podcastItems[0] ?? null,
    [podcastItems, activePodcastId],
  );

  const podcastAudio = useNotebookPodcastAudio(notebookId || null, activePodcast?.id ?? null, {
    enabled: Boolean(activePodcast && (activePodcast.audio_job_id || activePodcast.audio_status !== "not_ready")),
    refetchInterval:
      activePodcast && ["queued", "running"].includes(activePodcast.audio_status)
        ? 4000
        : false,
  });

  const activeAudio: NotebookPodcastAudioJob | null = podcastAudio.data ?? (activePodcast
    ? {
        notebook_id: activePodcast.notebook_id,
        script_id: activePodcast.id,
        title: activePodcast.title,
        audio_status: activePodcast.audio_status,
        audio_job_id: activePodcast.audio_job_id ?? null,
        audio_path: activePodcast.audio_path ?? null,
        audio_error: activePodcast.audio_error ?? null,
        created_at: activePodcast.created_at,
        updated_at: activePodcast.updated_at,
      }
    : null);

  useEffect(() => {
    if (!podcastAudio.data || !activePodcast) {
      return;
    }
    if (podcastAudio.data.audio_status !== activePodcast.audio_status || podcastAudio.data.audio_path !== activePodcast.audio_path) {
      void podcasts.refetch();
    }
  }, [activePodcast, podcastAudio.data, podcasts]);

  function toggleArticle(articleId: string) {
    setSelectedArticleIds((current) =>
      current.includes(articleId) ? current.filter((item) => item !== articleId) : [...current, articleId],
    );
  }

  function resetNotebookForm() {
    if (!notebookData) {
      return;
    }
    setName(notebookData.name);
    setEmoji(notebookData.emoji || "📒");
    setDescription(notebookData.description || "");
  }

  async function handleSaveNotebook() {
    if (!notebookData) {
      return;
    }
    await mutations.updateNotebook.mutateAsync({
      notebookId: notebookData.id,
      payload: {
        name: name.trim(),
        emoji: emoji.trim() || "📒",
        description: description.trim() || null,
      },
    });
  }

  async function handleAddArticles() {
    if (!notebookData || !selectedArticleIds.length) {
      return;
    }
    await mutations.addNotebookArticles.mutateAsync({
      notebookId: notebookData.id,
      articleIds: selectedArticleIds,
    });
    setSelectedArticleIds([]);
  }

  async function handleRemoveArticle(articleId: string, title: string) {
    if (!notebookData) {
      return;
    }
    if (!window.confirm(`确认将文章「${title}」从当前 Notebook 中移出吗？`)) {
      return;
    }
    await mutations.removeNotebookArticle.mutateAsync({ notebookId: notebookData.id, articleId });
  }

  async function handleAsk() {
    if (!notebookId || !chatInput.trim()) {
      return;
    }
    await mutations.askNotebookChat.mutateAsync({
      notebookId,
      message: chatInput.trim(),
    });
    setChatInput("");
  }

  async function handleClearChat() {
    if (!notebookId) {
      return;
    }
    if (!window.confirm("确认清空当前 Notebook 的对话历史吗？")) {
      return;
    }
    await mutations.clearNotebookChat.mutateAsync(notebookId);
  }

  async function handleGeneratePodcast() {
    if (!notebookId) {
      return;
    }
    const result = await mutations.generateNotebookPodcast.mutateAsync({
      notebookId,
      payload: {
        format: podcastFormat,
        targetMinutes: podcastMinutes,
        focusPrompt: podcastFocus.trim() || undefined,
      },
    });
    setActivePodcastId(result.id);
  }

  async function handleDeletePodcast(scriptId: string, title: string) {
    if (!notebookId) {
      return;
    }
    if (!window.confirm(`确认删除播客脚本「${title}」吗？`)) {
      return;
    }
    await mutations.deleteNotebookPodcast.mutateAsync({ notebookId, scriptId });
  }

  async function handleCopyPodcastMarkdown() {
    if (!activePodcast?.script_markdown) {
      return;
    }
    await navigator.clipboard.writeText(activePodcast.script_markdown);
    window.alert("播客脚本已复制到剪贴板。");
  }

  async function handleGenerateAudio() {
    if (!notebookId || !activePodcast) {
      return;
    }
    const isTencent = isTencentVoiceOption(audioVoice);
    await mutations.createNotebookPodcastAudio.mutateAsync({
      notebookId,
      scriptId: activePodcast.id,
      options: isTencent
        ? {
            engine: "tencent",
            voiceMode: audioVoice.slice(TENCENT_VOICE_PREFIX.length) as "female" | "male" | "duet",
          }
        : {
            engine: "edge",
            voice: audioVoice,
            rate: audioRate,
          },
    });
    await podcastAudio.refetch();
  }

  async function handleCopyAudioPath() {
    if (!activeAudio?.audio_path) {
      return;
    }
    await navigator.clipboard.writeText(activeAudio.audio_path);
    window.alert("音频路径已复制到剪贴板。");
  }

  return (
    <PageFrame
      title={notebookData ? `${notebookData.emoji || "📒"} ${notebookData.name}` : "Notebook"}
      subtitle="当前 Notebook 已经具备研究对话和 Podcast Studio。现在支持生成播客脚本，并可将脚本提交到独立 TTS worker 生成音频任务。"
      actions={
        <Link
          href="/notebooks"
          className="inline-flex items-center rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm text-white transition hover:bg-white/10"
        >
          <ArrowLeft size={14} className="mr-2" />
          返回列表
        </Link>
      }
    >
      {!notebookId ? (
        <EmptyState title="Notebook 不存在" description="当前路由没有有效的 Notebook 标识，请返回列表页重新进入。" />
      ) : notebook.isLoading ? (
        <EmptyState title="正在加载 Notebook" description="正在载入当前工作区的文章与基本信息。" />
      ) : !notebookData ? (
        <EmptyState title="Notebook 不存在" description="这个工作区可能已经被删除。返回列表页重新选择一个 Notebook。" />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.18fr)_420px]">
          <div className="space-y-6">
            <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.07),rgba(255,255,255,0.03))] p-5">
              <SectionTitle
                title="AI 对话"
                subtitle="当前版本不做多会话管理，只保留这一个连续对话区。问题会结合 Notebook 说明、最近几轮对话和已加入文章回答。"
              />

              <div className="rounded-[24px] border border-white/10 bg-[#0f1727]/80 p-4">
                <div className="flex h-[640px] min-h-[520px] flex-col">
                  <div className="scrollbar-dark min-h-0 flex-1 overflow-y-auto pr-2">
                    {!chatMessages.length ? (
                      <EmptyState
                        title="还没有对话记录"
                        description="先问一个问题，例如“这个 Notebook 里最值得继续跟踪的主题是什么？”或“请比较这些文章的主要分歧点”。"
                      />
                    ) : (
                      <div className="space-y-4">
                        {chatMessages.map((message) => (
                          <div
                            key={message.id}
                            className={`rounded-[22px] border px-4 py-4 ${
                              message.role === "user"
                                ? "ml-8 border-[#ffd478]/18 bg-[#ffd478]/8"
                                : "mr-8 border-white/10 bg-white/4"
                            }`}
                          >
                            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.22em] text-white/38">
                              <MessageSquare size={12} />
                              {message.role === "user" ? "Question" : "Answer"}
                            </div>
                            <div className="mt-3 whitespace-pre-wrap break-words text-sm leading-7 text-white/80">
                              {message.content}
                            </div>
                            {message.citations.length ? (
                              <div className="mt-4 flex flex-wrap gap-2">
                                {message.citations.map((citationId) => {
                                  const article = articleMap.get(citationId);
                                  if (!article) {
                                    return null;
                                  }
                                  return (
                                    <Link
                                      key={citationId}
                                      href={`/articles/${citationId}`}
                                      className="rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-xs text-white/72 transition hover:border-[#ffd478]/35 hover:text-[#ffe1a4]"
                                    >
                                      {article.title}
                                    </Link>
                                  );
                                })}
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="mt-5 grid shrink-0 gap-3 border-t border-white/10 pt-4">
                    <Textarea
                      value={chatInput}
                      onChange={(event) => setChatInput(event.target.value)}
                      placeholder="围绕当前 Notebook 提问。当前阶段会带上最近几轮对话和部分来源文章上下文，保持成本可控。"
                      className="min-h-32"
                    />
                    <div className="flex flex-wrap gap-3">
                      <ActionButton
                        variant="solid"
                        onClick={handleAsk}
                        disabled={!chatInput.trim() || mutations.askNotebookChat.isPending || !notebookData.article_count}
                      >
                        发送问题
                      </ActionButton>
                      <ActionButton
                        variant="ghost"
                        onClick={handleClearChat}
                        disabled={!chatMessages.length || mutations.clearNotebookChat.isPending}
                      >
                        清空对话
                      </ActionButton>
                    </div>
                    {!notebookData.article_count ? (
                      <p className="text-sm text-amber-200/72">当前 Notebook 里还没有文章来源，暂时不能提问。</p>
                    ) : null}
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.07),rgba(255,255,255,0.03))] p-5">
              <SectionTitle
                title="Podcast Studio"
                subtitle="当前阶段先生成播客脚本，不生成音频。脚本会以 section / turn / citation 的结构保存，为未来接入 TTS 和滚动文本预留空间。"
              />

              <div className="space-y-5">
                <div className="rounded-[24px] border border-white/10 bg-[#0f1727]/80 p-4">
                  <div className="flex items-center gap-2 text-white/85">
                    <Music4 size={16} />
                    <h3 className="text-sm font-semibold">生成配置</h3>
                  </div>

                  <div className="mt-4 grid gap-4 xl:grid-cols-2 2xl:grid-cols-[minmax(220px,0.9fr)_minmax(180px,0.55fr)_minmax(280px,1.4fr)_minmax(220px,0.95fr)]">
                    <div>
                      <label className="mb-2 block text-sm text-white/72">脚本格式</label>
                      <select
                        value={podcastFormat}
                        onChange={(event) => setPodcastFormat(event.target.value)}
                        className="w-full rounded-2xl border border-white/12 bg-white/5 px-4 py-3 text-sm text-white outline-none"
                      >
                        {PODCAST_FORMATS.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.label}
                          </option>
                        ))}
                      </select>
                      <p className="mt-2 text-sm leading-6 text-white/48">
                        {PODCAST_FORMATS.find((item) => item.value === podcastFormat)?.description}
                      </p>
                    </div>

                    <div>
                      <label className="mb-2 block text-sm text-white/72">目标时长</label>
                      <select
                        value={podcastMinutes}
                        onChange={(event) => setPodcastMinutes(Number(event.target.value) || 5)}
                        className="w-full rounded-2xl border border-white/12 bg-white/5 px-4 py-3 text-sm text-white outline-none"
                      >
                        <option value={3}>3 分钟</option>
                        <option value={5}>5 分钟</option>
                        <option value={8}>8 分钟</option>
                        <option value={10}>10 分钟</option>
                      </select>
                    </div>

                    <div>
                      <label className="mb-2 block text-sm text-white/72">重点提示</label>
                      <Textarea
                        value={podcastFocus}
                        onChange={(event) => setPodcastFocus(event.target.value)}
                        placeholder="例如：请重点比较这些文章对 AI Agent 商业化节奏的不同判断。"
                        className="min-h-[116px]"
                      />
                    </div>

                    <div className="flex flex-col justify-end gap-3">
                      <ActionButton
                        variant="solid"
                        onClick={handleGeneratePodcast}
                        disabled={!notebookData.article_count || mutations.generateNotebookPodcast.isPending}
                        className="w-full"
                      >
                        生成播客脚本
                      </ActionButton>
                      <div className="rounded-[18px] border border-dashed border-white/10 bg-white/4 px-4 py-3 text-sm leading-6 text-white/52">
                        先生成脚本，再在右侧选中的脚本卡片里提交音频任务。当前只显示状态，不做百分比进度。
                      </div>
                    </div>
                  </div>

                  {!notebookData.article_count ? (
                    <p className="mt-4 text-sm text-amber-200/72">当前 Notebook 中还没有文章来源，暂时不能生成播客脚本。</p>
                  ) : null}
                </div>

                <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_300px]">
                  <div className="rounded-[24px] border border-white/10 bg-[#0f1727]/80 p-4">
                    {!activePodcast ? (
                      <EmptyState title="还没有可查看的脚本" description="生成一份播客脚本后，这里会显示结构化脚本和未来的音频准备状态。" />
                    ) : (
                      <div className="flex h-[640px] flex-col">
                        {/* Script header */}
                        <div className="border-b border-white/10 pb-4">
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="rounded-full border border-white/10 bg-white/6 px-2.5 py-0.5 text-xs text-white/54">
                                  {podcastFormatLabel(activePodcast.format)}
                                </span>
                                <span className="rounded-full border border-white/10 bg-white/6 px-2.5 py-0.5 text-xs text-white/54">
                                  {activePodcast.target_minutes} min
                                </span>
                                <span className="rounded-full border border-white/10 bg-white/6 px-2.5 py-0.5 text-xs text-white/54">
                                  引用 {activePodcast.cited_article_ids.length} 篇
                                </span>
                              </div>
                              <h3 className="mt-2 text-xl font-semibold leading-snug text-white">{activePodcast.title}</h3>
                              {activePodcast.focus_prompt ? (
                                <p className="mt-1.5 text-sm leading-6 text-white/48">
                                  {activePodcast.focus_prompt}
                                </p>
                              ) : null}
                            </div>
                            <div className="flex shrink-0 items-center gap-2">
                              <ActionButton variant="ghost" onClick={handleCopyPodcastMarkdown}>
                                复制脚本
                              </ActionButton>
                              <ActionButton
                                variant="danger"
                                onClick={() => handleDeletePodcast(activePodcast.id, activePodcast.title)}
                                disabled={mutations.deleteNotebookPodcast.isPending}
                              >
                                删除
                              </ActionButton>
                            </div>
                          </div>
                        </div>

                        {/* Audio card */}
                        <div className="rounded-[18px] border border-white/10 bg-white/4 px-4 py-3">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <select
                                value={audioVoice}
                                onChange={(e) => setAudioVoice(e.target.value)}
                                className="rounded-lg border border-white/12 bg-white/6 px-3 py-1.5 text-xs text-white/80 outline-none"
                              >
                                <option value="zh-CN-XiaoxiaoNeural">小晓（女）</option>
                                <option value="zh-CN-YunyangNeural">云扬（男·播报）</option>
                                <option value="zh-CN-YunxiNeural">云希（男·自然）</option>
                                <option value="tencent:female">腾讯TTS-女声</option>
                                <option value="tencent:male">腾讯TTS-男声</option>
                                <option value="tencent:duet">腾讯TTS-男女双人</option>
                              </select>
                              <select
                                value={audioRate}
                                onChange={(e) => setAudioRate(e.target.value)}
                                disabled={isTencentVoiceOption(audioVoice)}
                                className="rounded-lg border border-white/12 bg-white/6 px-3 py-1.5 text-xs text-white/80 outline-none"
                              >
                                <option value="+0%">正常语速</option>
                                <option value="-8%">稍慢</option>
                                <option value="-15%">较慢</option>
                              </select>
                              <ActionButton
                                variant="solid"
                                onClick={handleGenerateAudio}
                                disabled={
                                  mutations.createNotebookPodcastAudio.isPending ||
                                  activeAudio?.audio_status === "queued" ||
                                  activeAudio?.audio_status === "running"
                                }
                              >
                                {activeAudio?.audio_status === "succeeded" ? "重新生成" : "生成音频"}
                              </ActionButton>
                            </div>
                            <div className="flex items-center gap-2">
                              <span
                                className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs ${
                                  activeAudio?.audio_status === "failed"
                                    ? "border-rose-400/30 bg-rose-400/10 text-rose-200"
                                    : activeAudio?.audio_status === "succeeded"
                                      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
                                      : "border-white/10 bg-white/6 text-white/54"
                                }`}
                              >
                                {audioStatusLabel(activeAudio?.audio_status)}
                              </span>
                              {(activeAudio?.audio_status === "queued" || activeAudio?.audio_status === "running") ? (
                                <div className="h-1.5 w-24 overflow-hidden rounded-full bg-white/8">
                                  <div className="h-full w-1/3 animate-pulse rounded-full bg-[#ffd478]/70" />
                                </div>
                              ) : null}
                              {activeAudio?.audio_path ? (
                                <ActionButton variant="ghost" onClick={handleCopyAudioPath}>
                                  复制路径
                                </ActionButton>
                              ) : null}
                            </div>
                          </div>
                          {activeAudio?.audio_error ? (
                            <p className="mt-2 text-sm leading-6 text-rose-200/85">{activeAudio.audio_error}</p>
                          ) : null}
                          {isTencentVoiceOption(audioVoice) ? (
                            <p className="mt-2 text-xs leading-5 text-white/36">腾讯 TTS 使用模块内默认语速配置，当前语速下拉仅对 Edge TTS 生效。</p>
                          ) : null}
                          {activeAudio?.audio_path ? (
                            <p className="mt-2 break-all font-mono text-xs leading-5 text-white/40">{activeAudio.audio_path}</p>
                          ) : !activeAudio?.audio_status || activeAudio.audio_status === "not_ready" ? (
                            <p className="mt-2 text-xs leading-5 text-white/36">选择声音和语速后点击生成，通常数秒完成。</p>
                          ) : null}
                        </div>

                        <div className="scrollbar-dark mt-5 min-h-0 flex-1 overflow-y-auto pr-2">
                          <div className="space-y-4">
                            {activePodcast.sections.map((section) => (
                              <div key={section.id} className="rounded-[18px] border border-white/10 bg-[#101827]/80 p-4">
                                <div className="flex items-center justify-between gap-3">
                                  <h4 className="text-base font-semibold text-white">{section.title}</h4>
                                  <span className="text-xs uppercase tracking-[0.2em] text-white/36">{section.turns.length} turn</span>
                                </div>
                                {section.objective ? (
                                  <p className="mt-2 text-sm leading-6 text-white/48">{section.objective}</p>
                                ) : null}
                                <div className="mt-3 space-y-3">
                                  {section.turns.map((turn, index) => (
                                    <div key={`${section.id}-${index}`} className="rounded-[16px] border border-white/8 bg-white/4 px-4 py-3">
                                      <p className="text-xs uppercase tracking-[0.2em] text-white/36">{turn.speaker_id}</p>
                                      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-white/78">{turn.text}</p>
                                      {turn.citations.length ? (
                                        <div className="mt-3 flex flex-wrap gap-2">
                                          {turn.citations.map((citationId) => {
                                            const article = articleMap.get(citationId);
                                            return article ? (
                                              <Link
                                                key={citationId}
                                                href={`/articles/${citationId}`}
                                                className="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs text-white/70 transition hover:border-[#ffd478]/35 hover:text-[#ffe1a4]"
                                              >
                                                {article.title}
                                              </Link>
                                            ) : null;
                                          })}
                                        </div>
                                      ) : null}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="rounded-[24px] border border-white/10 bg-[#0f1727]/80 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-sm font-semibold text-white">脚本历史</h3>
                      <span className="text-xs uppercase tracking-[0.22em] text-white/36">{podcastItems.length} items</span>
                    </div>
                    <div className="scrollbar-dark mt-3 max-h-[640px] space-y-2 overflow-y-auto pr-1">
                      {!podcastItems.length ? (
                        <p className="text-sm leading-6 text-white/45">还没有生成过播客脚本。先在上方配置格式和重点，再生成第一份脚本。</p>
                      ) : (
                        podcastItems.map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => setActivePodcastId(item.id)}
                            className={`w-full rounded-[18px] border px-3 py-3 text-left transition ${
                              activePodcast?.id === item.id
                                ? "border-[#ffd478]/32 bg-[#ffd478]/10"
                                : "border-white/10 bg-white/4 hover:bg-white/7"
                            }`}
                          >
                            <p className="line-clamp-3 text-sm font-medium leading-6 text-white">{item.title}</p>
                            <p className="mt-1 text-xs uppercase tracking-[0.2em] text-white/38">
                              {podcastFormatLabel(item.format)} / {item.target_minutes} min
                            </p>
                            <p className="mt-2 text-xs text-white/45">{new Date(item.created_at).toLocaleString("zh-CN")}</p>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.07),rgba(255,255,255,0.03))] p-5">
              <SectionTitle
                title="工作区来源"
                subtitle="这里收纳的是当前 Notebook 选中的来源文章。后续生成报告、播客脚本和其他文件时，也会优先基于这些文章组织内容。"
              />
              {!notebookData.articles.length ? (
                <EmptyState title="还没有加入任何文章" description="在右侧搜索文章并加入工作区。当前阶段先只支持本地文章数据库中的文章作为 Notebook 来源。" />
              ) : (
                <div className="grid gap-4">
                  {notebookData.articles.map((article) => (
                    <div
                      key={article.id}
                      className="rounded-[24px] border border-white/10 bg-[#101827]/80 p-5 shadow-[0_18px_50px_rgba(0,0,0,0.18)]"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <p className="text-xs uppercase tracking-[0.24em] text-white/38">{article.source_name}</p>
                          <Link href={`/articles/${article.id}`} className="mt-2 block text-lg leading-7 text-white hover:text-[#ffe1a4]">
                            {article.title}
                          </Link>
                          <p className="mt-2 text-sm text-white/52">{article.publish_time ?? "未知发布时间"}</p>
                        </div>
                        <ActionButton
                          variant="danger"
                          onClick={() => handleRemoveArticle(article.id, article.title)}
                          disabled={mutations.removeNotebookArticle.isPending}
                        >
                          <Trash2 size={14} className="mr-2" />
                          移出
                        </ActionButton>
                      </div>

                      {article.summary ? (
                        <div className="mt-4 rounded-[18px] border border-white/8 bg-white/4 px-4 py-3">
                          <p className="text-sm leading-7 text-white/66">{article.summary}</p>
                        </div>
                      ) : null}

                      <div className="mt-4 flex flex-wrap items-center gap-3">
                        <TagPills items={article.tags} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-[28px] border border-white/10 bg-[#0c1423]/82 p-5 shadow-glow">
              <SectionTitle title="Notebook 设置" subtitle="当前阶段只支持名称、emoji 和说明，先把工作区自身定义清楚。" />
              <div className="rounded-[22px] border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-white/38">图标</p>
                <div className="mt-3">
                  <EmojiPicker value={emoji} onChange={setEmoji} presets={EMOJI_PRESETS} placeholder="例如：📒" />
                </div>
              </div>

              <div className="mt-4">
                <label className="mb-2 block text-sm text-white/75">名称</label>
                <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Notebook 名称" maxLength={80} />
              </div>

              <div className="mt-4">
                <label className="mb-2 block text-sm text-white/75">说明</label>
                <Textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="介绍这个工作区想研究什么。对话、播客和报告都会把这里当作稳定背景。"
                  className="min-h-32"
                />
              </div>

              <div className="mt-5 flex gap-3">
                <ActionButton variant="solid" onClick={handleSaveNotebook} disabled={mutations.updateNotebook.isPending} className="flex-1">
                  保存设置
                </ActionButton>
                <ActionButton variant="ghost" onClick={resetNotebookForm}>
                  还原
                </ActionButton>
              </div>
            </section>

            <section className="rounded-[28px] border border-white/10 bg-[#0c1423]/82 p-5 shadow-glow">
              <SectionTitle title="加入文章" subtitle="先从本地文章库中挑选来源文章。当前不支持网页、文件等其他来源，后面再扩展。" />

              <div className="grid gap-3">
                <div className="rounded-[20px] border border-white/10 bg-white/5 p-4">
                  <label className="mb-2 block text-xs uppercase tracking-[0.22em] text-white/38">搜索文章</label>
                  <div className="relative">
                    <Search size={14} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-white/32" />
                    <Input
                      value={articleQuery}
                      onChange={(event) => setArticleQuery(event.target.value)}
                      placeholder="按标题、摘要、正文或来源名搜索"
                      className="pl-10"
                    />
                  </div>
                </div>

                <div className="rounded-[20px] border border-white/10 bg-white/5 p-4">
                  <label className="mb-2 block text-xs uppercase tracking-[0.22em] text-white/38">按来源过滤</label>
                  <select
                    value={sourceId}
                    onChange={(event) => setSourceId(event.target.value)}
                    className="w-full rounded-2xl border border-white/12 bg-white/5 px-4 py-3 text-sm text-white outline-none"
                  >
                    <option value="">全部来源</option>
                    {(sources.data ?? []).map((source) => (
                      <option key={source.id} value={source.id}>
                        {source.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-4 rounded-[20px] border border-dashed border-white/10 bg-white/4 px-4 py-3 text-sm leading-6 text-white/55">
                当前已选 {selectedArticleIds.length} 篇待加入文章。文章加入后不会从原始文章库删除，只会同时出现在这个工作区里。
              </div>

              <div className="mt-4 space-y-3">
                {candidateArticles.length ? (
                  candidateArticles.map((article) => (
                    <label
                      key={article.id}
                      className="flex cursor-pointer items-start gap-3 rounded-[20px] border border-white/10 bg-white/4 px-4 py-4 transition hover:bg-white/6"
                    >
                      <input
                        type="checkbox"
                        checked={selectedArticleIds.includes(article.id)}
                        onChange={() => toggleArticle(article.id)}
                        className="mt-1"
                      />
                      <div className="min-w-0">
                        <p className="text-xs uppercase tracking-[0.22em] text-white/36">{article.source_name}</p>
                        <p className="mt-1 text-sm leading-6 text-white">{article.title}</p>
                        <p className="mt-2 text-xs text-white/45">{article.publish_time ?? "未知发布时间"}</p>
                      </div>
                    </label>
                  ))
                ) : (
                  <EmptyState title="没有可加入的文章" description="试着更换搜索词或来源条件；如果当前页文章都已加入，这里会自动隐藏它们。" />
                )}
              </div>

              <ActionButton
                variant="solid"
                onClick={handleAddArticles}
                disabled={!selectedArticleIds.length || mutations.addNotebookArticles.isPending}
                className="mt-5 w-full"
              >
                <Plus size={14} className="mr-2" />
                加入已选文章
              </ActionButton>
            </section>
          </aside>
        </div>
      )}
    </PageFrame>
  );
}

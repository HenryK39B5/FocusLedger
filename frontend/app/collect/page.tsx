"use client";

import Link from "next/link";
import { AlertTriangle, ClipboardCopy, Play, RefreshCw, Save } from "lucide-react";
import { useMemo, useState } from "react";
import { useIngestionJobs, useMutations, useSources } from "@/lib/queries";
import type { IngestionJob } from "@/lib/types";
import {
  credentialStatusLabel,
  formatDateTimeShanghai,
  summarizeWechatCredentialLink,
  summarizeWechatHomeLink,
} from "@/lib/wechat";
import {
  ActionButton,
  EmptyState,
  Input,
  Label,
  PageFrame,
  SectionTitle,
  TagPills,
  Textarea,
} from "@/components/ui";

type SourceSyncSettings = {
  pageStart: number;
  pageEnd: number;
  sinceDays: string;
  dateFrom: string;
  dateTo: string;
};

const defaultSyncSettings: SourceSyncSettings = {
  pageStart: 1,
  pageEnd: 20,
  sinceDays: "7",
  dateFrom: "",
  dateTo: "",
};

function parseSinceDays(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return Math.floor(parsed);
}

function clampPage(value: number) {
  if (!Number.isFinite(value) || value < 1) return 1;
  return Math.floor(value);
}

function sourceStatusTone(status: string) {
  switch (status) {
    case "valid":
      return "border-emerald-400/30 bg-emerald-500/10 text-emerald-100";
    case "missing":
      return "border-slate-300/20 bg-slate-400/10 text-slate-100";
    case "refresh_required":
      return "border-amber-400/30 bg-amber-500/10 text-amber-100";
    case "invalid":
      return "border-red-400/30 bg-red-500/10 text-red-100";
    default:
      return "border-white/10 bg-white/5 text-white/70";
  }
}

function jobTone(status: string) {
  switch (status) {
    case "succeeded":
      return "text-emerald-200";
    case "failed":
      return "text-red-200";
    case "running":
      return "text-sky-200";
    case "pending":
      return "text-amber-200";
    default:
      return "text-white/70";
  }
}

function stageLabel(stage?: string | null) {
  switch (stage) {
    case "verifying_credential":
      return "验证凭据";
    case "fetching_article_list":
      return "获取文章列表";
    case "fetching_article_html":
      return "获取正文 HTML";
    case "parsing_article":
      return "解析正文";
    case "analyzing_with_llm":
      return "调用 LLM 整理";
    case "saving_article":
      return "写入文章";
    case "finalizing":
      return "收尾";
    default:
      return "排队中";
  }
}

function statusLabel(status: string) {
  switch (status) {
    case "succeeded":
      return "已完成";
    case "failed":
      return "失败";
    case "running":
      return "进行中";
    case "pending":
      return "排队中";
    case "cancelled":
      return "已取消";
    default:
      return status;
  }
}

function isActiveJob(job?: IngestionJob | null) {
  return job?.status === "pending" || job?.status === "running";
}

export default function CollectPage() {
  const sources = useSources();
  const jobs = useIngestionJobs({ limit: 100, refetchInterval: 1500 });
  const mutations = useMutations();

  const [message, setMessage] = useState("");
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [updatingCredentialId, setUpdatingCredentialId] = useState<string | null>(null);
  const [launchingJobId, setLaunchingJobId] = useState<string | null>(null);
  const [sourceSyncSettings, setSourceSyncSettings] = useState<Record<string, SourceSyncSettings>>({});
  const [credentialDrafts, setCredentialDrafts] = useState<Record<string, string>>({});

  const sourceRows = useMemo(() => sources.data ?? [], [sources.data]);
  const latestJobMap = useMemo(() => {
    const map = new Map<string, IngestionJob>();
    for (const job of jobs.data?.items ?? []) {
      if (!map.has(job.source_id)) {
        map.set(job.source_id, job);
      }
    }
    return map;
  }, [jobs.data]);

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

  function getCredentialDraft(sourceId: string, rawLink?: string | null) {
    return credentialDrafts[sourceId] ?? rawLink ?? "";
  }

  function updateCredentialDraft(sourceId: string, value: string) {
    setCredentialDrafts((current) => ({
      ...current,
      [sourceId]: value,
    }));
  }

  async function handleCopyHomeLink(sourceName: string, homeLink?: string | null) {
    if (!homeLink) {
      setMessage("当前来源缺少公众号主页链接。");
      return;
    }
    try {
      await navigator.clipboard.writeText(homeLink);
      setMessage(`已复制 ${sourceName} 的公众号主页链接。`);
    } catch {
      setMessage("复制公众号主页链接失败，请手动复制。");
    }
  }

  async function handleVerify(sourceId: string) {
    setVerifyingId(sourceId);
    try {
      const result = await mutations.verifySourceCredential.mutateAsync(sourceId);
      setMessage(result.message);
      await sources.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "验证来源凭据失败。");
    } finally {
      setVerifyingId(null);
    }
  }

  async function handleUpdateCredential(sourceId: string) {
    const rawLink = getCredentialDraft(sourceId).trim();
    if (!rawLink) {
      setMessage("请先粘贴新的 profile_ext 凭据链接。");
      return;
    }

    setUpdatingCredentialId(sourceId);
    try {
      await mutations.updateSourceCredential.mutateAsync({
        sourceId,
        rawLink,
        validateAfterUpdate: true,
      });
      setMessage("来源凭据已更新并完成验证。");
      await sources.refetch();
      await jobs.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "更新来源凭据失败。");
    } finally {
      setUpdatingCredentialId(null);
    }
  }

  async function handleCreateJob(sourceId: string) {
    const settings = getSourceSettings(sourceId);
    const trimmedDateFrom = settings.dateFrom.trim();
    const trimmedDateTo = settings.dateTo.trim();

    if (trimmedDateFrom && trimmedDateTo && trimmedDateFrom > trimmedDateTo) {
      setMessage("开始日期不能晚于结束日期。");
      return;
    }

    setLaunchingJobId(sourceId);
    try {
      const job = await mutations.createIngestionJob.mutateAsync({
        sourceId,
        pageStart: clampPage(settings.pageStart),
        pageEnd: clampPage(settings.pageEnd),
        sinceDays: trimmedDateFrom || trimmedDateTo ? null : parseSinceDays(settings.sinceDays),
        dateFrom: trimmedDateFrom || null,
        dateTo: trimmedDateTo || null,
      });
      setMessage(`同步任务已创建：${job.id}`);
      await jobs.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "创建同步任务失败。");
    } finally {
      setLaunchingJobId(null);
    }
  }

  return (
    <PageFrame
      title="文章获取"
      subtitle="这里负责凭据验证、手动更新凭据和文章同步。同步前系统会先验证 profile_ext 凭据；如果凭据已失效，请先手动更新，再重新发起同步。"
      actions={
        <>
          <Link href="/sources/add">
            <ActionButton variant="solid">添加公众号来源</ActionButton>
          </Link>
          <Link href="/sources">
            <ActionButton variant="ghost">来源管理</ActionButton>
          </Link>
          <ActionButton
            variant="ghost"
            onClick={() => {
              void Promise.all([sources.refetch(), jobs.refetch()]);
            }}
          >
            <RefreshCw size={14} className="mr-2" />
            刷新
          </ActionButton>
        </>
      }
    >
      <section className="mb-6 rounded-[28px] border border-amber-400/20 bg-amber-500/10 p-5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 shrink-0 text-amber-200" size={18} />
          <div className="text-sm leading-6 text-amber-50/90">
            <p className="font-medium text-amber-100">凭据需要手动更新</p>
            <p>
              系统会自动检测凭据是否可用。若某个来源显示“需要刷新凭据”或同步时提示凭据失效，请先在这里粘贴新的{" "}
              profile_ext 链接，再重新同步文章。
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
        <SectionTitle title="同步任务面板" subtitle="这里展示凭据状态、手动更新入口和最近一次同步任务结果。" />
        {message ? (
          <p className="mb-4 max-w-full whitespace-pre-wrap break-all rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm leading-6 text-white/70">
            {message}
          </p>
        ) : null}

        {!sourceRows.length ? (
          <EmptyState title="暂无来源" description="先去“添加公众号来源”页面创建来源，再回来执行同步。" />
        ) : (
          <div className="grid gap-4">
            {sourceRows.map((source) => {
              const settings = getSourceSettings(source.id);
              const latestJob = latestJobMap.get(source.id);
              const credentialDraft = getCredentialDraft(source.id, source.credential?.raw_link);
              const activeJob = isActiveJob(latestJob);

              return (
                <div key={source.id} className="min-w-0 rounded-[24px] border border-white/10 bg-black/20 p-5">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="text-lg text-white">{source.name}</h4>
                        <span className={`rounded-full border px-2.5 py-1 text-xs ${sourceStatusTone(source.credential_status)}`}>
                          {credentialStatusLabel(source.credential_status)}
                        </span>
                        {latestJob ? <span className={`text-xs ${jobTone(latestJob.status)}`}>任务：{statusLabel(latestJob.status)}</span> : null}
                      </div>
                      <p className="mt-2 break-all text-sm text-white/55">凭据：{summarizeWechatCredentialLink(source.credential?.raw_link)}</p>
                      <p className="mt-1 break-all text-sm text-white/55">主页：{summarizeWechatHomeLink(source.public_home_link, source.biz)}</p>
                      <p className="mt-1 text-xs text-white/45">biz：{source.biz}</p>
                      {source.tags.length ? (
                        <div className="mt-3">
                          <TagPills items={source.tags} />
                        </div>
                      ) : null}
                      <div className="mt-4 grid gap-2 whitespace-pre-wrap break-all text-xs leading-5 text-white/45 md:grid-cols-2">
                        <p>最后验证：{formatDateTimeShanghai(source.last_verified_at)}</p>
                        <p>最后成功同步：{formatDateTimeShanghai(source.last_sync_succeeded_at)}</p>
                        <p>最近失败：{formatDateTimeShanghai(source.last_sync_failed_at)}</p>
                        <p>错误代码：{source.last_error_code ?? "--"}</p>
                        <p className="md:col-span-2">最近错误：{source.last_error_message ?? "--"}</p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <ActionButton variant="ghost" onClick={() => handleVerify(source.id)} disabled={verifyingId === source.id}>
                        <RefreshCw size={14} className="mr-2" />
                        {verifyingId === source.id ? "验证中..." : "验证凭据"}
                      </ActionButton>
                      <ActionButton
                        variant="solid"
                        onClick={() => handleCreateJob(source.id)}
                        disabled={launchingJobId === source.id || activeJob}
                      >
                        <Play size={14} className="mr-2" />
                        {launchingJobId === source.id ? "创建任务中..." : activeJob ? "任务进行中" : "同步文章"}
                      </ActionButton>
                    </div>
                  </div>

                  <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
                    <div className="min-w-0 rounded-[20px] border border-white/10 bg-white/4 p-4">
                      <p className="text-sm text-white">同步参数</p>
                      <div className="mt-4 grid gap-4 md:grid-cols-3">
                        <div>
                          <Label>起始页</Label>
                          <Input
                            type="number"
                            min={1}
                            value={settings.pageStart}
                            onChange={(event) => updateSourceSettings(source.id, { pageStart: Number(event.target.value) })}
                          />
                        </div>
                        <div>
                          <Label>结束页</Label>
                          <Input
                            type="number"
                            min={1}
                            value={settings.pageEnd}
                            onChange={(event) => updateSourceSettings(source.id, { pageEnd: Number(event.target.value) })}
                          />
                        </div>
                        <div>
                          <Label>近几天</Label>
                          <Input
                            value={settings.sinceDays}
                            onChange={(event) =>
                              updateSourceSettings(source.id, {
                                sinceDays: event.target.value,
                                dateFrom: "",
                                dateTo: "",
                              })
                            }
                            placeholder="留空表示不限天数"
                          />
                        </div>
                      </div>

                      <div className="mt-4 rounded-[18px] border border-white/10 bg-black/20 p-4">
                        <p className="text-sm text-white">精确日期区间</p>
                        <p className="mt-1 text-xs leading-5 text-white/45">填写开始和结束日期后，会优先按日期区间同步，不再使用“近几天”。</p>
                        <div className="mt-4 grid gap-4 md:grid-cols-2">
                          <div>
                            <Label>开始日期</Label>
                            <Input
                              type="date"
                              value={settings.dateFrom}
                              onChange={(event) =>
                                updateSourceSettings(source.id, {
                                  dateFrom: event.target.value,
                                  sinceDays: "",
                                })
                              }
                            />
                          </div>
                          <div>
                            <Label>结束日期</Label>
                            <Input
                              type="date"
                              value={settings.dateTo}
                              onChange={(event) =>
                                updateSourceSettings(source.id, {
                                  dateTo: event.target.value,
                                  sinceDays: "",
                                })
                              }
                            />
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <ActionButton
                          variant="ghost"
                          onClick={() => updateSourceSettings(source.id, { sinceDays: "7", dateFrom: "", dateTo: "" })}
                        >
                          近 7 天
                        </ActionButton>
                        <ActionButton
                          variant="ghost"
                          onClick={() => updateSourceSettings(source.id, { sinceDays: "30", dateFrom: "", dateTo: "" })}
                        >
                          近 30 天
                        </ActionButton>
                        <ActionButton
                          variant="ghost"
                          onClick={() => updateSourceSettings(source.id, { sinceDays: "", dateFrom: "", dateTo: "" })}
                        >
                          清空范围
                        </ActionButton>
                      </div>
                    </div>

                    <div className="min-w-0 rounded-[20px] border border-white/10 bg-white/4 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm text-white">最近一次任务</p>
                          <p className="mt-1 text-xs text-white/50">
                            {latestJob ? `阶段：${stageLabel(latestJob.current_stage)}，状态：${statusLabel(latestJob.status)}` : "还没有执行过同步任务。"}
                          </p>
                          {latestJob?.date_from || latestJob?.date_to ? (
                            <p className="mt-1 text-xs text-white/40">
                              时间范围：{latestJob.date_from ?? "不限"} 至 {latestJob.date_to ?? "不限"}
                            </p>
                          ) : latestJob?.since_days ? (
                            <p className="mt-1 text-xs text-white/40">范围：近 {latestJob.since_days} 天</p>
                          ) : null}
                        </div>
                      </div>
                      {latestJob ? (
                        <div className="mt-4 min-w-0 grid gap-2 whitespace-pre-wrap break-all text-sm leading-6 text-white/75">
                          <p>当前文章：{latestJob.current_article_title ?? "--"}</p>
                          <p>
                            处理进度：{latestJob.processed_count}/{latestJob.total_candidates != null ? latestJob.total_candidates : "--"}
                          </p>
                          <p>
                            新增：{latestJob.imported_count} / 更新：{latestJob.updated_count} / 失败：{latestJob.failed_count}
                          </p>
                          <p>提示：{latestJob.message ?? "--"}</p>
                          <p>
                            开始：{formatDateTimeShanghai(latestJob.started_at)} / 结束：{formatDateTimeShanghai(latestJob.finished_at)}
                          </p>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-5 min-w-0 rounded-[20px] border border-white/10 bg-white/4 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm text-white">手动更新凭据</p>
                        <p className="mt-1 text-xs text-white/50">当凭据失效、需要刷新或你已经拿到新的 profile_ext 链接时，在这里手动粘贴并更新。</p>
                      </div>
                      <ActionButton
                        variant={source.credential_status === "refresh_required" ? "solid" : "ghost"}
                        onClick={() => handleUpdateCredential(source.id)}
                        disabled={updatingCredentialId === source.id}
                      >
                        <Save size={14} className="mr-2" />
                        {updatingCredentialId === source.id ? "更新中..." : "更新凭据"}
                      </ActionButton>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <ActionButton
                        variant="ghost"
                        onClick={() => handleCopyHomeLink(source.name, source.public_home_link)}
                        disabled={!source.public_home_link}
                      >
                        <ClipboardCopy size={14} className="mr-2" />
                        复制公众号主页链接
                      </ActionButton>
                    </div>
                    <div className="mt-4">
                      <Textarea
                        value={credentialDraft}
                        onChange={(event) => updateCredentialDraft(source.id, event.target.value)}
                        placeholder="粘贴新的 https://mp.weixin.qq.com/mp/profile_ext?action=report&..."
                      />
                    </div>
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

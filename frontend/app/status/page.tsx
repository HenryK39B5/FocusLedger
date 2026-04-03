"use client";

import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { ActionButton, EmptyState, PageFrame, SectionTitle, StatCard } from "@/components/ui";
import { useSources, useStatus } from "@/lib/queries";

function formatStatusValue(value: unknown) {
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  if (value == null) {
    return "--";
  }
  return String(value);
}

export default function StatusPage() {
  const status = useStatus();
  const sources = useSources();

  return (
    <PageFrame
      title="系统状态"
      subtitle="查看当前环境、服务配置和来源规模，便于快速确认系统状态。"
      actions={
        <ActionButton variant="ghost" onClick={() => status.refetch()}>
          <RefreshCw size={14} className="mr-2" />
          刷新状态
        </ActionButton>
      }
    >
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="来源数" value={String(sources.data?.length ?? 0)} hint="当前已保存的公众号来源" />
        <StatCard label="环境" value={formatStatusValue(status.data?.environment)} hint="后端运行环境" />
        <StatCard
          label="LLM Provider"
          value={formatStatusValue(status.data?.llm_provider)}
          hint="摘要、Notebook 对话与脚本生成使用的分析后端"
        />
        <StatCard
          label="自动建表"
          value={formatStatusValue(status.data?.auto_create_schema)}
          hint="启动时是否自动初始化数据表"
        />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle title="原始状态输出" subtitle="这里保留后端状态接口的原始 JSON，便于调试。" />
          {status.data ? (
            <pre className="overflow-x-auto rounded-[24px] border border-white/10 bg-black/20 p-5 text-sm leading-6 text-white/75">
              {JSON.stringify(status.data, null, 2)}
            </pre>
          ) : (
            <EmptyState title="状态未返回" description="确认后端已启动，并检查 `/api/v1/system/status` 是否可访问。" />
          )}
        </section>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle title="操作入口" subtitle="按下面顺序使用系统会更稳定。" />
          <div className="space-y-4 text-sm leading-6 text-white/70">
            <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
              <p className="text-white">1. 添加和整理来源</p>
              <p className="mt-2">先在采集页面创建公众号来源，再在来源管理页面维护分组和标签。</p>
              <Link href="/collect" className="mt-3 inline-block text-[#ffd478] hover:underline">
                前往公众号采集
              </Link>
            </div>
            <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
              <p className="text-white">2. 同步和浏览文章</p>
              <p className="mt-2">同步后去文章浏览页面做筛选、删除和批量清理。</p>
              <Link href="/articles" className="mt-3 inline-block text-[#ffd478] hover:underline">
                前往文章浏览
              </Link>
            </div>
            <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
              <p className="text-white">3. 进入 Notebook</p>
              <p className="mt-2">把文章加入工作区后，继续做 AI 对话、脚本生成和后续内容编排。</p>
              <Link href="/notebooks" className="mt-3 inline-block text-[#ffd478] hover:underline">
                前往 Notebooks
              </Link>
            </div>
          </div>
        </section>
      </div>
    </PageFrame>
  );
}

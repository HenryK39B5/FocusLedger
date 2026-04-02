"use client";

import { cn } from "@/lib/utils";
import {
  BookOpen,
  Database,
  FileText,
  FolderKanban,
  FolderPlus,
  Rss,
  Settings2,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(255,204,112,0.20),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(78,110,255,0.18),_transparent_26%),linear-gradient(180deg,_#0c1220_0%,_#09101a_100%)] text-fg">
      <div className="mx-auto flex min-h-screen max-w-[1600px]">{children}</div>
    </div>
  );
}

export function Sidebar() {
  const items = [
    { href: "/", label: "总览", icon: Database },
    { href: "/sources/add", label: "添加来源", icon: FolderPlus },
    { href: "/sources", label: "来源管理", icon: FolderKanban },
    { href: "/collect", label: "文章获取", icon: Rss },
    { href: "/articles", label: "文章浏览", icon: BookOpen },
    { href: "/reports", label: "日报生成", icon: FileText },
    { href: "/status", label: "系统状态", icon: Settings2 },
  ];

  return (
    <aside className="hidden w-72 shrink-0 border-r border-white/10 bg-black/15 px-5 py-6 backdrop-blur xl:block">
      <div className="overflow-hidden rounded-[30px] border border-white/10 bg-[linear-gradient(160deg,rgba(255,255,255,0.10),rgba(255,255,255,0.03))] p-5 shadow-glow">
        <p className="text-[11px] uppercase tracking-[0.4em] text-white/45">FocusLedger</p>
        <h1 className="mt-4 font-[family-name:var(--font-display)] text-[2rem] leading-[1.15] text-white">
          公众号研究台
        </h1>
        <p className="mt-3 max-w-[18rem] text-sm leading-6 text-white/58">
          把来源、文章、标签和日报放进同一套本地工作流。
        </p>
        <div className="mt-5 grid gap-2">
          <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-3 text-xs text-white/62">
            先同步，再整理，再输出。
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3 text-xs text-white/52">
            当前主线：文章管理、标签体系、Notebook 化工作区。
          </div>
        </div>
      </div>

      <nav className="mt-8 space-y-2">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 rounded-2xl border border-white/8 bg-white/4 px-4 py-3 text-sm text-white/75 transition hover:border-white/16 hover:bg-white/8 hover:text-white"
          >
            <item.icon size={16} />
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="mt-8 rounded-3xl border border-white/10 bg-white/5 p-4 text-sm text-white/60">
        <div className="flex items-center gap-2 text-white/85">
          <Sparkles size={14} />
          当前模式
        </div>
        <p className="mt-2 leading-6">
          凭据更新维持手动流程。当前更重要的能力是文章整理、标签管理、研究工作区和日报输出。
        </p>
      </div>
    </aside>
  );
}

export function PageFrame({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main className="flex-1 px-5 py-5 lg:px-8 lg:py-8">
      <div className="rounded-[32px] border border-white/10 bg-white/6 p-6 shadow-glow backdrop-blur">
        <div className="flex flex-col gap-5 border-b border-white/10 pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.32em] text-white/45">FocusLedger / 本地工作台</p>
            <h2 className="mt-2 font-[family-name:var(--font-display)] text-3xl text-white">{title}</h2>
            {subtitle ? <p className="mt-2 max-w-3xl text-sm leading-6 text-white/60">{subtitle}</p> : null}
          </div>
          {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
        </div>
        <div className="pt-6">{children}</div>
      </div>
    </main>
  );
}

export function StatCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
      <p className="text-xs uppercase tracking-[0.28em] text-white/45">{label}</p>
      <div className="mt-4 text-3xl font-semibold text-white">{value}</div>
      {hint ? <p className="mt-2 text-sm text-white/55">{hint}</p> : null}
    </div>
  );
}

export function TagPills({ items }: { items: string[] }) {
  const uniqueItems = Array.from(
    new Set(
      items
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  );

  if (!uniqueItems.length) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {uniqueItems.map((item, index) => (
        <span
          key={`${item}-${index}`}
          className="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs text-white/70"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        <h3 className="text-xl font-semibold text-white">{title}</h3>
        {subtitle ? <p className="mt-1 text-sm text-white/55">{subtitle}</p> : null}
      </div>
    </div>
  );
}

export function ActionButton({
  children,
  variant = "solid",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "solid" | "ghost" | "danger" }) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "solid" && "bg-white text-slate-950 hover:bg-white/90",
        variant === "ghost" && "border border-white/15 bg-white/5 text-white hover:bg-white/10",
        variant === "danger" && "border border-red-400/30 bg-red-500/15 text-red-100 hover:bg-red-500/25",
        props.className,
      )}
    >
      {children}
    </button>
  );
}

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        "w-full rounded-2xl border border-white/12 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-white/30 focus:border-white/25",
        className,
      )}
    />
  );
}

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cn(
        "min-h-28 w-full rounded-2xl border border-white/12 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-white/30 focus:border-white/25",
        className,
      )}
    />
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <label className="mb-2 block text-sm text-white/75">{children}</label>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-[28px] border border-dashed border-white/15 bg-white/4 p-8 text-center">
      <p className="text-lg font-medium text-white">{title}</p>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-white/55">{description}</p>
    </div>
  );
}

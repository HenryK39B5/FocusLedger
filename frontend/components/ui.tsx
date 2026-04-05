"use client";

import { cn } from "@/lib/utils";
import {
  BookOpen,
  Database,
  FolderKanban,
  FolderPlus,
  NotebookPen,
  ScrollText,
  Rss,
  Settings2,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { SmilePlus } from "lucide-react";
import { useState } from "react";

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(255,204,112,0.18),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(78,110,255,0.15),_transparent_28%),linear-gradient(180deg,_#0c1220_0%,_#09101a_100%)] text-fg">
      <div className="mx-auto flex min-h-screen max-w-[1600px]">{children}</div>
    </div>
  );
}

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  exact?: boolean;
};

const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "来源",
    items: [
      { href: "/", label: "总览", icon: Database, exact: true },
      { href: "/sources/add", label: "添加来源", icon: FolderPlus, exact: true },
      { href: "/sources", label: "来源管理", icon: FolderKanban },
      { href: "/collect", label: "文章获取", icon: Rss },
    ],
  },
  {
    label: "研究",
    items: [
      { href: "/articles", label: "文章浏览", icon: BookOpen },
      { href: "/reports", label: "日报生成", icon: ScrollText },
      { href: "/notebooks", label: "Notebooks", icon: NotebookPen },
    ],
  },
  {
    label: "系统",
    items: [{ href: "/status", label: "系统状态", icon: Settings2 }],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  function isActive(item: NavItem) {
    if (item.exact) {
      return pathname === item.href;
    }
    return pathname === item.href || pathname.startsWith(item.href + "/");
  }

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-white/8 bg-black/18 px-4 py-5 backdrop-blur xl:flex">
      <div className="flex items-center gap-3 px-1 pb-5">
        <img src="/favicon.svg" alt="FocusLedger" className="h-8 w-8 rounded-lg" />
        <div>
          <p className="text-sm font-semibold text-white">FocusLedger</p>
          <p className="text-[11px] text-white/40">公众号研究台</p>
        </div>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <p className="mb-1.5 px-3 text-[10px] font-medium uppercase tracking-[0.32em] text-white/30">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active = isActive(item);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition",
                      active
                        ? "border-l-2 border-[#f7c66b] bg-white/8 pl-[10px] text-white"
                        : "text-white/55 hover:bg-white/5 hover:text-white/80",
                    )}
                  >
                    <item.icon
                      size={15}
                      className={active ? "text-[#f7c66b]" : "text-white/40"}
                    />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="mt-4 border-t border-white/8 pt-4">
        <p className="px-3 text-[11px] leading-5 text-white/28">先同步，再整理，再研究。</p>
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
    <main className="flex-1 overflow-hidden px-5 py-5 lg:px-7 lg:py-6">
      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-[1.8rem] leading-tight text-white">{title}</h2>
          {subtitle ? <p className="mt-1.5 max-w-2xl text-[13px] leading-6 text-white/52">{subtitle}</p> : null}
        </div>
        {actions ? <div className="flex flex-shrink-0 flex-wrap gap-2">{actions}</div> : null}
      </div>
      <div>{children}</div>
    </main>
  );
}

export function StatCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-[22px] border border-white/10 bg-white/5 px-4 py-4 shadow-[0_12px_30px_rgba(0,0,0,0.12)]">
      <p className="text-[10px] uppercase tracking-[0.26em] text-white/40">{label}</p>
      <div className="mt-2.5 text-[1.75rem] font-semibold text-white">{value}</div>
      {hint ? <p className="mt-1.5 text-[13px] leading-6 text-white/48">{hint}</p> : null}
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
    <div className="flex flex-wrap gap-1.5">
      {uniqueItems.map((item, index) => (
        <span
          key={`${item}-${index}`}
          className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-white/62"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3.5">
      <h3 className="text-[1.05rem] font-semibold text-white">{title}</h3>
      {subtitle ? <p className="mt-1 text-[13px] leading-6 text-white/50">{subtitle}</p> : null}
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
        "inline-flex items-center justify-center rounded-full px-3.5 py-2 text-[13px] font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "solid" && "bg-white text-slate-950 hover:bg-white/90",
        variant === "ghost" && "border border-white/15 bg-white/5 text-white/84 hover:bg-white/10",
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
        "w-full rounded-[18px] border border-white/12 bg-white/5 px-3.5 py-2.5 text-[13px] text-white outline-none placeholder:text-white/28 focus:border-white/24",
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
        "min-h-28 w-full rounded-[18px] border border-white/12 bg-white/5 px-3.5 py-2.5 text-[13px] text-white outline-none placeholder:text-white/28 focus:border-white/24",
        className,
      )}
    />
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <label className="mb-1.5 block text-[12px] uppercase tracking-[0.2em] text-white/42">{children}</label>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-[24px] border border-dashed border-white/12 bg-white/3 p-7 text-center">
      <p className="text-[15px] font-medium text-white">{title}</p>
      <p className="mx-auto mt-2 max-w-xl text-[13px] leading-6 text-white/48">{description}</p>
    </div>
  );
}

export function EmojiPicker({
  value,
  onChange,
  presets,
  placeholder = "输入 emoji",
}: {
  value: string;
  onChange: (value: string) => void;
  presets: string[];
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setOpen((current) => !current)}
          className="flex h-12 min-w-12 items-center justify-center rounded-[16px] border border-white/12 bg-white/6 text-2xl transition hover:border-white/20 hover:bg-white/9"
          aria-label="选择 Notebook 图标"
        >
          {value || "📒"}
        </button>
        <div className="flex-1">
          <Input
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder={placeholder}
            maxLength={8}
          />
        </div>
        <ActionButton variant="ghost" type="button" onClick={() => setOpen((current) => !current)}>
          <SmilePlus size={14} className="mr-2" />
          {open ? "收起选项" : "选择图标"}
        </ActionButton>
      </div>
      {open ? (
        <div className="rounded-[18px] border border-white/10 bg-black/20 p-3">
          <div className="flex flex-wrap gap-2">
            {presets.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => {
                  onChange(item);
                  setOpen(false);
                }}
                className={cn(
                  "rounded-[14px] border px-3 py-2 text-xl transition",
                  value === item
                    ? "border-[#f7c66b]/40 bg-[#f7c66b]/12"
                    : "border-white/10 bg-white/4 hover:border-white/18 hover:bg-white/8",
                )}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

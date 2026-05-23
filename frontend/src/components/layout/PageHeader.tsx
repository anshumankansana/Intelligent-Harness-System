import Link from "next/link";
import { Plus } from "lucide-react";
import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow = "// MISSION CONTROL",
  title,
  description,
  showNewProject = true,
  statusPill,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  showNewProject?: boolean;
  statusPill?: { label: string; variant: "awaiting" | "live" | "error" | "running" };
}) {
  const pillClass = {
    awaiting: "border-amber-500/50 bg-amber-500/10 text-amber-300",
    live: "border-emerald-500/50 bg-emerald-500/10 text-emerald-300",
    error: "border-red-500/50 bg-red-500/10 text-red-300",
    running: "border-cyan-500/50 bg-cyan-500/10 text-harness-cyan",
  };

  return (
    <div className="flex flex-col gap-4 border-b border-harness-border bg-harness-surface/50 px-8 py-6 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 flex-1">
        <p className="section-label mb-2">{eyebrow}</p>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">{title}</h1>
          {statusPill && (
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                pillClass[statusPill.variant]
              )}
            >
              {statusPill.variant === "awaiting" && (
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
              )}
              {statusPill.label}
            </span>
          )}
        </div>
        {description && (
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">{description}</p>
        )}
      </div>
      {showNewProject && (
        <Link href="/new" className="btn-cyan shrink-0 self-start">
          <Plus className="h-4 w-4" />
          New Project
        </Link>
      )}
    </div>
  );
}

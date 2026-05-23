"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HarnessProject } from "@/store/harnessStore";

function statusLabel(p: HarnessProject) {
  if (p.status === "awaiting")
    return { text: "awaiting", class: "text-amber-400 border-amber-500/40 bg-amber-500/10" };
  if (p.status === "live")
    return { text: "done", class: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10" };
  if (p.status === "failed")
    return { text: "failed", class: "text-red-400 border-red-500/40 bg-red-500/10" };
  if (p.status === "building" || p.status === "planning")
    return { text: "running", class: "text-harness-cyan border-cyan-500/40 bg-cyan-500/10" };
  return { text: p.status, class: "text-slate-400 border-harness-border bg-white/5" };
}

export function RecentProjectsList({ projects }: { projects: HarnessProject[] }) {
  if (!projects.length) return null;

  const sorted = [...projects].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );

  return (
    <section className="px-8 pb-8">
      <div className="stat-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-harness-border px-5 py-3.5">
          <h2 className="text-sm font-semibold text-white">Recent projects</h2>
          <span className="font-mono text-[10px] text-harness-muted">{projects.length} total</span>
        </div>
        <ul className="divide-y divide-harness-border/60">
          {sorted.slice(0, 8).map((p) => {
            const badge = statusLabel(p);
            const href =
              p.status === "awaiting"
                ? `/approval?run=${p.id}`
                : p.phase === "DEBATE"
                  ? `/debate?run=${p.id}`
                  : `/logs?run=${p.id}`;
            return (
              <li key={p.id}>
                <Link
                  href={href}
                  className="flex items-center gap-4 px-5 py-3.5 transition hover:bg-white/[0.02]"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium capitalize text-white">{p.title}</p>
                    <p className="mt-0.5 font-mono text-[10px] text-harness-muted">
                      {p.phase} · {p.progress}%
                    </p>
                  </div>
                  <span
                    className={cn(
                      "shrink-0 rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                      badge.class
                    )}
                  >
                    {badge.text}
                  </span>
                  <ChevronRight className="h-4 w-4 shrink-0 text-harness-muted" />
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

"use client";

import Link from "next/link";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HarnessProject } from "@/store/harnessStore";

export type ApprovalItem = {
  id: string;
  title: string;
  stage: string;
  approvalStatus: string;
  isPending: boolean;
};

export function ApprovalQueue({
  items,
  selectedId,
  onSelect,
  expandedHistory,
  onToggleHistory,
}: {
  items: ApprovalItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  expandedHistory: Set<string>;
  onToggleHistory: (id: string) => void;
}) {
  const pending = items.filter((i) => i.isPending);
  const done = items.filter((i) => !i.isPending);

  return (
    <aside className="stat-card w-full shrink-0 overflow-hidden lg:w-72">
      <div className="border-b border-harness-border px-4 py-3">
        <p className="text-sm font-semibold text-white">Approval queue</p>
        <p className="text-[10px] text-harness-muted">
          {pending.length} pending · {done.length} completed
        </p>
      </div>

      {pending.length > 0 && (
        <div className="p-2">
          <p className="section-label px-2 py-1">Needs action</p>
          <ul className="space-y-1">
            {pending.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelect(item.id)}
                  className={cn(
                    "w-full rounded-lg border px-3 py-2.5 text-left transition",
                    selectedId === item.id
                      ? "border-red-500/50 bg-red-500/10"
                      : "border-amber-500/30 bg-amber-500/5 hover:border-amber-500/50",
                    selectedId === item.id && "approval-nav-blink"
                  )}
                >
                  <p className="truncate text-sm font-medium capitalize text-white">
                    {item.title}
                  </p>
                  <p className="font-mono text-[10px] text-amber-300">Awaiting approval</p>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {done.length > 0 && (
        <div className="border-t border-harness-border p-2">
          <p className="section-label px-2 py-1">Completed</p>
          <ul className="space-y-1">
            {done.map((item) => {
              const open = expandedHistory.has(item.id);
              const approved = item.approvalStatus === "approved";
              return (
                <li key={item.id} className="rounded-lg border border-harness-border/80">
                  <button
                    type="button"
                    onClick={() => {
                      onSelect(item.id);
                      onToggleHistory(item.id);
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2.5 text-left hover:bg-white/[0.03]"
                  >
                    {open ? (
                      <ChevronDown className="h-4 w-4 shrink-0 text-harness-muted" />
                    ) : (
                      <ChevronRight className="h-4 w-4 shrink-0 text-harness-muted" />
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm capitalize text-slate-300">{item.title}</p>
                      <p
                        className={cn(
                          "text-[10px] font-bold uppercase",
                          approved ? "text-emerald-400" : "text-red-400"
                        )}
                      >
                        {approved ? "Approved" : "Rejected"}
                      </p>
                    </div>
                  </button>
                  {open && selectedId === item.id && (
                    <div className="border-t border-harness-border/60 px-3 py-2">
                      <Link
                        href={`/logs?run=${item.id}`}
                        className="text-xs text-harness-cyan hover:underline"
                      >
                        View run logs →
                      </Link>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {items.length === 0 && (
        <p className="p-4 text-sm text-slate-500">No projects yet.</p>
      )}
    </aside>
  );
}

"use client";

import Link from "next/link";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export type DebateItem = {
  id: string;
  title: string;
  complete: boolean;
  messageCount: number;
};

export function DebateQueue({
  items,
  selectedId,
  onSelect,
  expandedHistory,
  onToggleHistory,
}: {
  items: DebateItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  expandedHistory: Set<string>;
  onToggleHistory: (id: string) => void;
}) {
  const live = items.filter((i) => !i.complete);
  const done = items.filter((i) => i.complete);

  return (
    <aside className="stat-card w-full shrink-0 overflow-hidden lg:w-72">
      <div className="border-b border-harness-border px-4 py-3">
        <p className="text-sm font-semibold text-white">Debate sessions</p>
        <p className="text-[10px] text-harness-muted">
          {live.length} in progress · {done.length} completed
        </p>
      </div>

      {live.length > 0 && (
        <div className="p-2">
          <p className="section-label px-2 py-1">Live</p>
          <ul className="space-y-1">
            {live.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelect(item.id)}
                  className={cn(
                    "w-full rounded-lg border px-3 py-2.5 text-left transition",
                    selectedId === item.id
                      ? "border-harness-cyan/50 bg-harness-cyan/10"
                      : "border-harness-border hover:border-harness-cyan/30"
                  )}
                >
                  <p className="truncate text-sm font-medium capitalize text-white">{item.title}</p>
                  <p className="font-mono text-[10px] text-harness-cyan">
                    {item.messageCount > 0 ? "Debate running…" : "Starting…"}
                  </p>
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
                      <p className="text-[10px] font-bold uppercase text-emerald-400">Complete</p>
                    </div>
                  </button>
                  {open && selectedId === item.id && (
                    <div className="space-y-2 border-t border-harness-border/60 px-3 py-2">
                      <Link
                        href={`/approval?run=${item.id}`}
                        className="block text-xs text-harness-cyan hover:underline"
                      >
                        Go to approval →
                      </Link>
                      <Link
                        href={`/logs?run=${item.id}`}
                        className="block text-xs text-slate-400 hover:underline"
                      >
                        View logs
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

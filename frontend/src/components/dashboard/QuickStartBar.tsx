"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Play } from "lucide-react";
import { useHarnessStore } from "@/store/harnessStore";

const SUGGESTIONS = [
  "Build a todo app with auth",
  "Create a REST API service",
  "Generate a dashboard UI",
  "Expense tracker — free hosting only",
];

export function QuickStartBar() {
  const router = useRouter();
  const setUserIdea = useHarnessStore((s) => s.setUserIdea);

  const pick = (text: string) => {
    setUserIdea(text);
    router.push("/new");
  };

  return (
    <div className="mx-8 mb-6 stat-card p-5">
      <p className="section-label mb-3">// Quick launch</p>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
        <p className="flex-1 text-sm text-slate-400">
          Describe what to build — the harness plans, debates, and ships with your approval.
        </p>
        <Link href="/new" className="btn-cyan shrink-0">
          <Play className="h-4 w-4" />
          Run harness
        </Link>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => pick(s)}
            className="rounded-full border border-harness-border bg-harness-bg/80 px-3 py-1.5 text-xs text-slate-400 transition hover:border-harness-cyan/40 hover:text-harness-cyan"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

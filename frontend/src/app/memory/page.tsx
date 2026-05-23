"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/layout/PageHeader";
import { MemoryDocument } from "@/components/memory/MemoryDocument";
import { useHarnessStore } from "@/store/harnessStore";
import { getMemory } from "@/lib/api";
import { cn } from "@/lib/utils";

const FILE_ORDER = [
  "PROJECT_SPEC.md",
  "TASKS.md",
  "ARCHITECTURE.md",
  "DECISIONS.md",
  "RISKS.md",
  "TEST_PLAN.md",
  "DEBATE_SUMMARY.md",
];

const FILE_LABELS: Record<string, string> = {
  "PROJECT_SPEC.md": "Specification",
  "TASKS.md": "Tasks",
  "ARCHITECTURE.md": "Architecture",
  "DECISIONS.md": "Decisions",
  "RISKS.md": "Risks",
  "TEST_PLAN.md": "Test plan",
  "DEBATE_SUMMARY.md": "Debate",
};

function MemoryContent() {
  const searchParams = useSearchParams();
  const runParam = searchParams.get("run");
  const { runId, setRunId, memoryFiles, setMemoryFiles } = useHarnessStore();
  const activeRun = runParam || runId;
  const [selected, setSelected] = useState("PROJECT_SPEC.md");

  useEffect(() => {
    if (runParam) setRunId(runParam);
  }, [runParam, setRunId]);

  useEffect(() => {
    if (!activeRun) return;
    const load = async () => {
      const data = await getMemory(activeRun);
      setMemoryFiles(data.files || {});
    };
    load();
    const interval = setInterval(load, 4000);
    return () => clearInterval(interval);
  }, [activeRun, setMemoryFiles]);

  const files = Object.keys(memoryFiles).sort(
    (a, b) => FILE_ORDER.indexOf(a) - FILE_ORDER.indexOf(b)
  );

  const content = memoryFiles[selected] || "";

  return (
    <>
      <PageHeader
        eyebrow="// MEMORY"
        title="Engineering Documents"
        description="Clean, readable specs and plans — formatted for review before build."
        showNewProject={false}
      />

      <div className="flex min-h-[calc(100vh-180px)]">
        <aside className="w-56 shrink-0 border-r border-harness-border bg-harness-surface/40 p-4">
          {!activeRun && (
            <p className="text-xs text-slate-500">Open a project from the Dashboard</p>
          )}
          <p className="section-label mb-3">Documents</p>
          <ul className="space-y-1">
            {files.map((f) => (
              <li key={f}>
                <button
                  onClick={() => setSelected(f)}
                  className={cn(
                    "w-full rounded px-3 py-2.5 text-left text-sm transition",
                    selected === f
                      ? "bg-harness-cyan/15 text-harness-cyan font-medium"
                      : "text-slate-400 hover:bg-white/5 hover:text-white"
                  )}
                >
                  <span className="block">{FILE_LABELS[f] || f}</span>
                  <span className="block font-mono text-[9px] text-harness-muted mt-0.5">
                    {f}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <div className="flex-1 overflow-y-auto bg-harness-bg/50 p-6 lg:p-10">
          {content ? (
            <MemoryDocument content={content} filename={selected} />
          ) : (
            <div className="panel max-w-lg p-8 text-slate-400 text-sm">
              Waiting for the planner to generate documents…
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default function MemoryPage() {
  return (
    <Suspense fallback={<div className="p-8 text-slate-500">Loading…</div>}>
      <MemoryContent />
    </Suspense>
  );
}

"use client";

import { useEffect, useRef, Suspense, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { PageHeader } from "@/components/layout/PageHeader";
import { DebateMessageBubble, TypingIndicator } from "@/components/debate/DebateMessage";
import { DebateQueue } from "@/components/debate/DebateQueue";
import { useHarnessSocket } from "@/hooks/useHarnessSocket";
import { useDebateStore } from "@/store/debateStore";
import { useHarnessStore } from "@/store/harnessStore";
import { getDebate } from "@/lib/api";
import { avatarUrl } from "@/store/debateStore";
import Image from "next/image";

function DebateContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const runParam = searchParams.get("run");
  const { runId, setRunId, projects } = useHarnessStore();
  const activeRun = runParam || runId;

  const {
    agents,
    messages,
    typingAgentId,
    complete,
    actionItems,
    loadFromApi,
  } = useDebateStore();

  const scrollRef = useRef<HTMLDivElement>(null);
  const [queueMeta, setQueueMeta] = useState<
    Record<string, { complete: boolean; messageCount: number }>
  >({});
  const [expandedHistory, setExpandedHistory] = useState<Set<string>>(new Set());

  useHarnessSocket(activeRun);

  useEffect(() => {
    if (runParam) setRunId(runParam);
  }, [runParam, setRunId]);

  const refreshQueue = useCallback(async () => {
    const meta: Record<string, { complete: boolean; messageCount: number }> = {};
    for (const p of projects) {
      try {
        const d = await getDebate(p.id);
        meta[p.id] = {
          complete: Boolean(d.complete),
          messageCount: d.transcript?.length ?? 0,
        };
      } catch {
        meta[p.id] = { complete: false, messageCount: 0 };
      }
    }
    setQueueMeta(meta);
  }, [projects]);

  useEffect(() => {
    refreshQueue();
    const interval = setInterval(refreshQueue, 4000);
    return () => clearInterval(interval);
  }, [refreshQueue]);

  useEffect(() => {
    if (!activeRun) return;
    getDebate(activeRun).then(loadFromApi).catch(() => {});
  }, [activeRun, loadFromApi]);

  useEffect(() => {
    if (complete && activeRun) {
      setExpandedHistory((prev) => new Set(prev).add(activeRun));
      refreshQueue();
    }
  }, [complete, activeRun, refreshQueue]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, typingAgentId]);

  const typingAgent = agents.find((a) => a.id === typingAgentId);

  const queueItems = projects.map((p) => {
    const m = queueMeta[p.id];
    return {
      id: p.id,
      title: p.title,
      complete: m?.complete ?? false,
      messageCount: m?.messageCount ?? 0,
    };
  });

  const selectRun = (id: string) => {
    setRunId(id);
    router.push(`/debate?run=${id}`);
  };

  const toggleHistory = (id: string) => {
    setExpandedHistory((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const debateEnded =
    complete || Boolean(activeRun && queueMeta[activeRun]?.complete);
  const showLivePanel = activeRun && !debateEnded;

  return (
    <>
      <PageHeader
        eyebrow="// DEBATE CHAMBER"
        title="Live Agent Debate"
        description="Live debates stay open. Completed sessions collapse in the list — click to review and go to approval."
        showNewProject={false}
      />

      <div className="flex flex-col gap-6 px-8 pb-8 lg:flex-row">
        <DebateQueue
          items={queueItems}
          selectedId={activeRun}
          onSelect={selectRun}
          expandedHistory={expandedHistory}
          onToggleHistory={toggleHistory}
        />

        <div className="min-w-0 flex-1">
          {!activeRun ? (
            <div className="panel p-8 text-center text-slate-400">
              Select a project from the queue, or start one from the dashboard.
            </div>
          ) : (
            <div className="grid gap-6 lg:grid-cols-[200px_1fr]">
              <aside className="panel p-4 h-fit">
                <p className="section-label mb-3">// Agents</p>
                <ul className="space-y-3">
                  {agents.map((a) => (
                    <li key={a.id} className="flex items-center gap-2">
                      <Image
                        src={avatarUrl(a.avatar_seed, a.color)}
                        alt={a.name}
                        width={36}
                        height={36}
                        className="rounded-full border"
                        style={{ borderColor: a.color }}
                        unoptimized
                      />
                      <div>
                        <p className="text-xs font-medium text-white">{a.name}</p>
                        <p className="text-[10px] text-harness-muted">{a.title}</p>
                      </div>
                    </li>
                  ))}
                  {agents.length === 0 && !debateEnded && (
                    <p className="text-xs text-slate-500">Waiting for debate to start…</p>
                  )}
                  {debateEnded && agents.length === 0 && (
                    <p className="text-xs text-slate-500">Debate finished — reload to refresh agents.</p>
                  )}
                </ul>
                <p className="mt-4 font-mono text-[10px] text-harness-muted">run {activeRun}</p>
              </aside>

              <div className="flex flex-col">
                {debateEnded && !showLivePanel ? (
                  <div className="panel border-l-4 border-l-harness-green p-5">
                    <p className="section-label mb-2">// Debate complete</p>
                    <p className="text-sm text-slate-300 mb-4">
                      This session is done. Review action items, then approve in the Approval Center.
                    </p>
                    {actionItems.length > 0 && (
                      <ul className="mb-4 space-y-1 text-sm text-slate-400">
                        {actionItems.map((item, i) => (
                          <li key={i} className="flex gap-2">
                            <span className="text-harness-cyan">{i + 1}.</span>
                            {item}
                          </li>
                        ))}
                      </ul>
                    )}
                    <div className="flex flex-wrap gap-3">
                      <Link href={`/approval?run=${activeRun}`} className="btn-cyan text-sm">
                        Go to Approval Center
                      </Link>
                      <Link
                        href={`/memory?run=${activeRun}`}
                        className="rounded border border-harness-border px-4 py-2 text-sm text-slate-300 hover:bg-white/5"
                      >
                        View Memory
                      </Link>
                    </div>
                  </div>
                ) : (
                  <>
                    <div
                      ref={scrollRef}
                      className="panel flex-1 space-y-4 overflow-y-auto p-5 min-h-[420px] max-h-[calc(100vh-320px)]"
                    >
                      {messages.length === 0 && !typingAgentId && (
                        <p className="text-center text-sm text-harness-muted py-12">
                          Debate will appear here live as each agent speaks…
                        </p>
                      )}
                      {messages.map((m) => (
                        <DebateMessageBubble key={`${m.turn_index}-${m.agent_id}`} message={m} />
                      ))}
                      {typingAgent && (
                        <TypingIndicator
                          name={typingAgent.name}
                          color={typingAgent.color}
                          seed={typingAgent.avatar_seed}
                        />
                      )}
                    </div>
                    {messages.length > 0 && !complete && (
                      <p className="mt-2 text-center text-xs text-harness-muted animate-pulse">
                        Debate in progress…
                      </p>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default function DebatePage() {
  return (
    <Suspense fallback={<div className="p-8 text-slate-500">Loading debate…</div>}>
      <DebateContent />
    </Suspense>
  );
}

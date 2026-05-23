"use client";

import { useCallback, useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/layout/PageHeader";
import { useHarnessStore } from "@/store/harnessStore";
import { useHarnessSocket } from "@/hooks/useHarnessSocket";
import {
  getRun,
  getRunLogs,
  getDebate,
  resumeRun,
  continueFallback,
  publishGitHub,
  publishDeploy,
  downloadProjectZipUrl,
  updateProjectRun,
  type RunStatus,
} from "@/lib/api";
import { PipelineStepper } from "@/components/harness/PipelineStepper";
import { LogTerminal } from "@/components/harness/LogTerminal";
import { AgentFindingsPanel } from "@/components/harness/AgentFindingsPanel";
import type { DebateMessage } from "@/store/debateStore";
import { cn } from "@/lib/utils";
import { isDeployInProgress, mergeProjectPatchFromStage } from "@/lib/runStage";

function RunStatusPanel({
  status,
  runId,
  onResume,
  onContinueFallback,
  onRefresh,
  loading,
}: {
  status: RunStatus | null;
  runId: string;
  onResume: () => void;
  onContinueFallback: () => void;
  onRefresh: () => void;
  loading: boolean;
}) {
  if (!status) return null;

  const isLive = status.stage === "complete";
  const isReady = status.stage === "ready_to_publish";
  const isError = status.stage === "error" || status.stage === "validation_failed";
  const isWaiting = status.stage === "awaiting_approval";
  const isFallback = status.stage === "awaiting_fallback" || status.fallback?.pending;
  const isDeploying = isDeployInProgress(status.stage, status.context?.deploy_url);

  return (
    <div
      className={cn(
        "panel mb-6 border-l-4 p-5",
        isError && "border-l-red-500",
        (isWaiting || isFallback) && "border-l-amber-500",
        (isLive || isReady) && "border-l-emerald-500",
        !isError && !isWaiting && !isLive && !isReady && "border-l-harness-cyan"
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="section-label mb-1">// Current step</p>
          <h2 className="text-lg font-semibold text-white">{status.stage_label}</h2>
          <p className="mt-1 font-mono text-xs text-harness-muted">
            run {runId} · {status.progress}% · stage: {status.stage}
          </p>
          {isDeploying && (
            <p className="mt-2 text-sm text-cyan-200/90 max-w-2xl">
              Vercel deploy in progress — npm build may finish first, then vercel link/deploy runs
              (can take several minutes). Watch for &quot;Still running vercel…&quot; heartbeats in
              the log below.
            </p>
          )}
          {status.error && (
            <p className="mt-2 text-sm text-red-400 max-w-2xl">{status.error}</p>
          )}
          {status.memory_files.length > 0 && (
            <p className="mt-2 text-xs text-slate-500">
              Memory: {status.memory_files.join(", ")}
            </p>
          )}
        </div>
        <div className="h-2 w-32 overflow-hidden rounded-full bg-harness-border self-center">
          <div
            className="h-full bg-harness-cyan transition-all"
            style={{ width: `${status.progress}%` }}
          />
        </div>
      </div>

      <div className="mt-4">
        <p className="section-label mb-2">// What you can do</p>
        <div className="flex flex-wrap gap-2">
          {status.fallback?.pending && status.fallback.chain.length > 0 && (
            <p className="mb-3 text-sm text-amber-100/90">
              Provider failed — harness is auto-trying:{" "}
              <strong>{status.fallback.chain.join(" → ")}</strong>
            </p>
          )}
          {status.next_actions.map((a) => {
            if (a.action === "publish_github") {
              return (
                <button
                  key={a.label}
                  type="button"
                  disabled={loading || isDeploying}
                  onClick={async () => {
                    const r = await publishGitHub(runId);
                    if (!r.ok) alert(r.error);
                    onRefresh();
                  }}
                  className="btn-cyan text-xs"
                >
                  {a.label}
                </button>
              );
            }
            if (a.action === "publish_deploy") {
              return (
                <button
                  key={a.label}
                  type="button"
                  disabled={loading || isDeploying}
                  onClick={async () => {
                    const r = await publishDeploy(runId);
                    if (!r.ok) alert(r.error);
                    onRefresh();
                  }}
                  className="rounded border border-emerald-500/50 px-3 py-1.5 text-xs font-semibold text-emerald-400"
                >
                  {a.label}
                </button>
              );
            }
            if (a.action === "download_zip") {
              return (
                <a
                  key={a.label}
                  href={downloadProjectZipUrl(runId)}
                  className="rounded border border-harness-border px-3 py-1.5 text-xs text-slate-300 hover:text-white"
                >
                  {a.label}
                </a>
              );
            }
            if (a.action === "update") {
              return (
                <button
                  key={a.label}
                  type="button"
                  onClick={async () => {
                    const text = window.prompt("What should change in this project?");
                    if (!text?.trim()) return;
                    await updateProjectRun(runId, text.trim());
                    onRefresh();
                  }}
                  className="rounded border border-amber-500/40 px-3 py-1.5 text-xs text-amber-300"
                >
                  {a.label}
                </button>
              );
            }
            if (a.action === "continue_fallback" || a.action === "refresh") {
              return null;
            }
            if (a.action === "resume") {
              return (
                <button
                  key={a.label}
                  onClick={onResume}
                  disabled={loading}
                  className="btn-cyan text-xs"
                >
                  {loading ? "Resuming…" : a.label}
                </button>
              );
            }
            if (a.action === "refresh") {
              return (
                <button
                  key={a.label}
                  onClick={() => window.location.reload()}
                  className="rounded border border-harness-border px-3 py-1.5 text-xs text-slate-300 hover:bg-white/5"
                >
                  {a.label}
                </button>
              );
            }
            if (a.href) {
              const href = a.href.includes("?")
                ? a.href
                : a.href === "/memory"
                  ? `/memory`
                  : a.href;
              const fullHref =
                a.href === "/approval" || a.href.startsWith("/approval")
                  ? `/approval?run=${runId}`
                  : a.href === "/memory"
                    ? `/memory?run=${runId}`
                    : href;
              return (
                <Link key={a.label} href={fullHref} className="btn-cyan text-xs">
                  {a.label}
                </Link>
              );
            }
            return null;
          })}
        </div>
      </div>

      {isWaiting && (
        <p className="mt-3 text-sm text-amber-200/90">
          The harness is paused until you approve the plan. Open{" "}
          <Link href={`/approval?run=${runId}`} className="text-harness-cyan underline">
            Approval Center
          </Link>{" "}
          and click <strong>Approve</strong>.
        </p>
      )}
    </div>
  );
}

function LogsContent() {
  const searchParams = useSearchParams();
  const runParam = searchParams.get("run");
  const { runId, setRunId, logs, setLogsForRun, addLog, updateProject } = useHarnessStore();
  const activeRun = runParam || runId;

  const [status, setStatus] = useState<RunStatus | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [debateMessages, setDebateMessages] = useState<DebateMessage[]>([]);
  const [debateSummary, setDebateSummary] = useState("");
  const [actionItems, setActionItems] = useState<string[]>([]);

  useHarnessSocket(activeRun);

  const refreshStatus = useCallback(async () => {
    if (!activeRun) return;
    try {
      const data = await getRun(activeRun);
      setStatus(data);
      const gh = data.context?.github_url || "";
      const dep = data.context?.deploy_url || "";
      const p = useHarnessStore.getState().projects.find((x) => x.id === activeRun);
      if (p) {
        const patch = mergeProjectPatchFromStage(p, data.stage, {
          approvalStatus: data.approval?.status,
          githubUrl: gh,
          deployUrl: dep,
          projectMode: data.project_mode,
        });
        if (Object.keys(patch).length) updateProject(activeRun, patch);
      }
    } catch {
      /* backend offline */
    }
  }, [activeRun, updateProject]);

  const loadPersistedLogs = useCallback(async () => {
    if (!activeRun) return;
    try {
      const { logs: saved } = await getRunLogs(activeRun);
      if (saved.length > 0) {
        setLogsForRun(saved);
      }
    } catch {
      /* no logs yet */
    }
  }, [activeRun, setLogsForRun]);

  const loadDebate = useCallback(async () => {
    if (!activeRun) return;
    try {
      const d = await getDebate(activeRun);
      setDebateMessages(d.transcript || []);
      setDebateSummary(d.summary || "");
      setActionItems(d.action_items || []);
    } catch {
      /* optional */
    }
  }, [activeRun]);

  useEffect(() => {
    if (runParam) setRunId(runParam);
  }, [runParam, setRunId]);

  useEffect(() => {
    if (!activeRun) return;
    loadPersistedLogs();
    loadDebate();
    refreshStatus();
    const interval = setInterval(() => {
      refreshStatus();
      loadDebate();
    }, 4000);
    return () => clearInterval(interval);
  }, [activeRun, loadPersistedLogs, loadDebate, refreshStatus]);

  const handleContinueFallback = async () => {
    if (!activeRun) return;
    setResumeLoading(true);
    try {
      const res = await continueFallback(activeRun);
      addLog(
        `Fallback continue — trying: ${(res.chain as string[])?.join(" → ") || "next providers"}`
      );
      await refreshStatus();
    } catch (e) {
      addLog(`Continue failed: ${e}`);
    } finally {
      setResumeLoading(false);
    }
  };

  const handleResume = async () => {
    if (!activeRun) return;
    setResumeLoading(true);
    try {
      await resumeRun(activeRun);
      addLog("Resume requested — builder / validation continuing...");
      await refreshStatus();
    } catch (e) {
      addLog(`Resume failed: ${e}`);
    } finally {
      setResumeLoading(false);
    }
  };

  const displayLogs = logs.length > 0 ? logs : [];

  return (
    <>
      <PageHeader
        eyebrow="// LIVE HARNESS"
        title="Run Command Center"
        description="Pipeline progress, live execution log, and agent findings for this run."
        showNewProject={false}
        statusPill={
          status
            ? {
                label:
                  status.stage === "awaiting_approval"
                    ? "awaiting approval"
                    : status.stage_label,
                variant:
                  status.stage === "awaiting_approval"
                    ? "awaiting"
                    : status.stage === "complete"
                      ? "live"
                      : status.stage === "error"
                        ? "error"
                        : "running",
              }
            : undefined
        }
      />

      <div className="px-8 py-6">
        {!activeRun ? (
          <div className="panel p-8 text-center text-slate-400">
            <p>No run selected.</p>
            <Link href="/" className="mt-4 inline-block text-harness-cyan">
              Back to Dashboard
            </Link>
          </div>
        ) : (
          <>
            <RunStatusPanel
              status={status}
              runId={activeRun}
              onResume={handleResume}
              onContinueFallback={handleContinueFallback}
              onRefresh={refreshStatus}
              loading={resumeLoading}
            />

            <div className="grid gap-6 xl:grid-cols-12">
              <div className="xl:col-span-3">
                {status && (
                  <PipelineStepper stage={status.stage} progress={status.progress} />
                )}
              </div>

              <div className="xl:col-span-6">
                <div className="mb-3 flex items-center justify-between">
                  <p className="font-mono text-xs text-harness-muted">Execution log · {activeRun}</p>
                  <button
                    type="button"
                    onClick={() => loadPersistedLogs()}
                    className="text-xs uppercase tracking-wider text-slate-500 hover:text-harness-cyan"
                  >
                    Reload
                  </button>
                </div>
                <div className="log-terminal h-[calc(100vh-380px)] min-h-[320px] overflow-y-auto">
                  {displayLogs.length === 0 ? (
                    <div className="text-harness-muted space-y-2 text-sm">
                      <p>No log lines yet.</p>
                      <p className="text-xs">Start a run or resume from the status panel above.</p>
                    </div>
                  ) : (
                    <LogTerminal lines={displayLogs} />
                  )}
                </div>
              </div>

              <div className="xl:col-span-3">
                <AgentFindingsPanel
                  messages={debateMessages}
                  actionItems={actionItems}
                  summary={debateSummary}
                />
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}

export default function LogsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-slate-500">Loading…</div>}>
      <LogsContent />
    </Suspense>
  );
}

"use client";

import { useEffect, useState, Suspense, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/card";
import { ApprovalQueue } from "@/components/approval/ApprovalQueue";
import { ApprovalDocumentPanel } from "@/components/approval/ApprovalDocumentPanel";
import { ApprovalActionBar } from "@/components/approval/ApprovalActionBar";
import {
  isPendingApproval,
  isResolvedApproval,
  isDebateInProgress,
  showApprovalActions,
} from "@/components/approval/approvalState";
import { DebateWaitingBanner } from "@/components/approval/DebateWaitingBanner";
import {
  APPROVAL_DOCUMENTS,
  type ApprovalDocKey,
  type DocPanelState,
  buildDocsFromMemory,
  emptyDocState,
} from "@/components/approval/approvalDocuments";
import { useHarnessStore } from "@/store/harnessStore";
import Link from "next/link";
import { getRun, getDebate, getMemory, submitApproval } from "@/lib/api";
import { projectPatchFromStage } from "@/lib/runStage";
import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, ArrowRight } from "lucide-react";

function ApprovalContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const runParam = searchParams.get("run");
  const { runId, setRunId, projects, updateProject } = useHarnessStore();
  const activeRun = runParam || runId;
  const [loading, setLoading] = useState(false);
  const [actionItems, setActionItems] = useState<string[]>([]);
  const [docs, setDocs] = useState<Record<string, DocPanelState>>(() => buildDocsFromMemory({}));
  const [activeDoc, setActiveDoc] = useState<ApprovalDocKey>("PROJECT_SPEC.md");
  const [projectMode, setProjectMode] = useState("new");
  const [importIntent, setImportIntent] = useState<
    "deploy_only" | "edit_deploy" | "continue_build"
  >("edit_deploy");
  const [runStage, setRunStage] = useState("");
  const [approvalStatus, setApprovalStatus] = useState("none");
  const [queueMeta, setQueueMeta] = useState<
    Record<string, { stage: string; approvalStatus: string }>
  >({});
  const [expandedHistory, setExpandedHistory] = useState<Set<string>>(new Set());
  const [debateComplete, setDebateComplete] = useState(false);

  const updateDoc = (key: ApprovalDocKey, patch: Partial<DocPanelState>) => {
    setDocs((prev) => ({
      ...prev,
      [key]: { ...emptyDocState(), ...prev[key], ...patch },
    }));
  };

  const refreshQueue = useCallback(async () => {
    const meta: Record<string, { stage: string; approvalStatus: string }> = {};
    for (const p of projects) {
      try {
        const data = await getRun(p.id);
        const stage = data.stage || "";
        const st =
          stage === "awaiting_approval" ? "pending" : data.approval?.status || "none";
        meta[p.id] = { stage, approvalStatus: st };
        if (stage === "awaiting_approval" || st === "pending") {
          updateProject(
            p.id,
            projectPatchFromStage(stage, {
              approvalStatus: st,
              githubUrl: data.context?.github_url,
              deployUrl: data.context?.deploy_url,
              projectMode: data.project_mode,
            })
          );
        }
      } catch {
        meta[p.id] = { stage: "unknown", approvalStatus: "none" };
      }
    }
    setQueueMeta(meta);
  }, [projects, updateProject]);

  useEffect(() => {
    if (runParam) setRunId(runParam);
  }, [runParam, setRunId]);

  useEffect(() => {
    refreshQueue();
    const interval = setInterval(refreshQueue, 4000);
    return () => clearInterval(interval);
  }, [refreshQueue]);

  useEffect(() => {
    if (!activeRun) return;
    const load = async () => {
      const data = await getRun(activeRun);
      const stage = data.stage || "";
      let apiStatus = data.approval?.status || "none";
      if (stage === "awaiting_approval") {
        apiStatus = "pending";
      }
      setRunStage(stage);
      setApprovalStatus(apiStatus);
      setProjectMode(data.project_mode || "new");
      if (stage === "awaiting_approval") {
        updateProject(
          activeRun,
          projectPatchFromStage(stage, {
            approvalStatus: apiStatus,
            githubUrl: data.context?.github_url,
            deployUrl: data.context?.deploy_url,
            projectMode: data.project_mode,
          })
        );
      }
    };
    const loadDebate = async () => {
      try {
        const d = await getDebate(activeRun);
        setActionItems(d.action_items || []);
        setDebateComplete(Boolean(d.complete));
      } catch {
        setActionItems([]);
        setDebateComplete(false);
      }
    };
    const loadMemory = async () => {
      try {
        const mem = await getMemory(activeRun);
        setDocs(buildDocsFromMemory(mem.files));
      } catch {
        setDocs(buildDocsFromMemory({}));
      }
    };
    load();
    loadDebate();
    loadMemory();
    const interval = setInterval(() => {
      load();
      loadDebate();
      loadMemory();
    }, 4000);
    return () => clearInterval(interval);
  }, [activeRun, updateProject]);

  const queueItems = projects.map((p) => {
    const m = queueMeta[p.id];
    const stage = m?.stage ?? "";
    const st = m?.approvalStatus ?? "none";
    return {
      id: p.id,
      title: p.title,
      stage,
      approvalStatus: st,
      isPending: isPendingApproval(stage, st),
    };
  });

  const queuePending = activeRun
    ? (queueItems.find((q) => q.id === activeRun)?.isPending ?? false)
    : false;

  const pending = activeRun
    ? isPendingApproval(runStage, approvalStatus) || queuePending
    : false;
  const resolved = activeRun ? isResolvedApproval(runStage, approvalStatus) : false;
  const showActions = activeRun
    ? showApprovalActions(runStage, approvalStatus) || queuePending
    : false;

  const isApproved =
    approvalStatus === "approved" || (resolved && approvalStatus !== "rejected");
  const isRejected = approvalStatus === "rejected";
  const isUpdate = projectMode === "update";
  const debateInProgress = activeRun
    ? isDebateInProgress(runStage, debateComplete)
    : false;

  const selectRun = (id: string) => {
    setRunId(id);
    router.push(`/approval?run=${id}`);
  };

  const toggleHistory = (id: string) => {
    setExpandedHistory((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const payloadFromDocs = () => {
    const document_instructions: Record<string, string> = {};
    for (const { key } of APPROVAL_DOCUMENTS) {
      if (docs[key]?.instructions?.trim()) {
        document_instructions[key] = docs[key].instructions.trim();
      }
    }
    return { document_instructions };
  };

  const hasAnyInstructions = APPROVAL_DOCUMENTS.some((d) =>
    docs[d.key]?.instructions?.trim()
  );

  const handleApprove = async () => {
    if (!activeRun) return;
    if (!hasAnyInstructions) {
      const ok = window.confirm(
        "You have not added instructions on any document tab.\n\nApprove and continue to build anyway?"
      );
      if (!ok) return;
    }
    setLoading(true);
    const payload = payloadFromDocs();
    await submitApproval(
      activeRun,
      "approved",
      "",
      "",
      projectMode === "import" ? importIntent : undefined,
      {},
      payload.document_instructions
    );
    setApprovalStatus("approved");
    setRunStage("approved");
    updateProject(activeRun, { status: "building", phase: "DEVELOPMENT", progress: 55 });
    setExpandedHistory((prev) => new Set(prev).add(activeRun));
    setLoading(false);
    refreshQueue();
  };

  const handleReject = async () => {
    if (!activeRun) return;
    setLoading(true);
    const payload = payloadFromDocs();
    await submitApproval(
      activeRun,
      "rejected",
      "",
      "",
      undefined,
      {},
      payload.document_instructions
    );
    setApprovalStatus("rejected");
    updateProject(activeRun, { status: "failed", phase: "REJECTED", progress: 0 });
    setExpandedHistory((prev) => new Set(prev).add(activeRun));
    setLoading(false);
    refreshQueue();
  };

  return (
    <>
      <PageHeader
        eyebrow="// APPROVAL"
        title="Approval Center"
        description="Review each document (read-only), add optional per-document instructions, then approve the whole package."
        showNewProject={false}
      />

      <div className="flex flex-col gap-6 px-8 py-6 lg:flex-row">
        <ApprovalQueue
          items={queueItems}
          selectedId={activeRun}
          onSelect={selectRun}
          expandedHistory={expandedHistory}
          onToggleHistory={toggleHistory}
        />

        <div className="min-w-0 flex-1">
          {!activeRun && (
            <Card>
              <p className="text-sm text-slate-400">
                Select a project from the queue, or start one from the dashboard.
              </p>
            </Card>
          )}

          {activeRun && (
            <>
              <div className="mb-4 flex items-center justify-between">
                <p className="font-mono text-xs text-harness-muted">run {activeRun}</p>
                {pending && (
                  <span className="badge-awaiting animate-pulse">Awaiting you</span>
                )}
                {showActions && !pending && (
                  <span className="badge-awaiting animate-pulse">Action required</span>
                )}
                {resolved && isApproved && !pending && (
                  <span className="badge-approved">Approved</span>
                )}
                {isRejected && (
                  <span className="rounded border border-red-500/50 bg-red-500/15 px-2 py-0.5 text-[10px] font-bold uppercase text-red-400">
                    Rejected
                  </span>
                )}
              </div>

              {debateInProgress && (
                <DebateWaitingBanner runId={activeRun} stage={runStage} />
              )}

              {pending && !debateInProgress && (
                <div className="approval-panel-pending relative z-10 space-y-5 rounded-lg p-6">
                  <div className="flex items-center gap-2 border-b border-red-500/30 pb-4">
                    <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" />
                    <p className="text-sm font-semibold text-red-200">
                      {isUpdate
                        ? "Update review — read docs, add instructions, then approve to rebuild"
                        : "Read each document → add instructions → approve whole package"}
                    </p>
                  </div>

                  {actionItems.length > 0 && (
                    <Card title="// Debate action items">
                      <ul className="space-y-2 text-sm text-slate-300">
                        {actionItems.map((item, i) => (
                          <li key={i} className="flex gap-2">
                            <span className="font-mono text-harness-cyan">{i + 1}.</span>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </Card>
                  )}

                  <ApprovalDocumentPanel
                    docs={docs}
                    activeDoc={activeDoc}
                    onActiveDoc={setActiveDoc}
                    onUpdateDoc={updateDoc}
                    disabled={loading}
                  />

                  {projectMode === "import" && (
                    <Card title="// Imported project — what should we do?">
                      <div className="space-y-2 text-sm">
                        {(
                          [
                            { id: "deploy_only" as const, label: "Complete — only deploy" },
                            { id: "edit_deploy" as const, label: "Needs edits, then deploy" },
                            { id: "continue_build" as const, label: "Half-done — continue building" },
                          ] as const
                        ).map((opt) => (
                          <label
                            key={opt.id}
                            className={cn(
                              "flex cursor-pointer gap-3 rounded-lg border p-3",
                              importIntent === opt.id && "border-harness-cyan/50 bg-harness-cyan/5"
                            )}
                          >
                            <input
                              type="radio"
                              name="import_intent"
                              checked={importIntent === opt.id}
                              onChange={() => setImportIntent(opt.id)}
                            />
                            <span className="text-white">{opt.label}</span>
                          </label>
                        ))}
                      </div>
                    </Card>
                  )}

                  <ApprovalActionBar
                    onApprove={handleApprove}
                    onReject={handleReject}
                    loading={loading}
                    sticky
                  />
                </div>
              )}

              {resolved && !pending && !showActions && (
                <>
                  <div
                    className={cn(
                      "mb-6 p-6",
                      isApproved
                        ? "approval-panel-approved rounded-lg"
                        : "approval-panel-rejected rounded-lg"
                    )}
                  >
                    <div className="flex items-start gap-4">
                      {isApproved ? (
                        <CheckCircle2 className="h-10 w-10 shrink-0 text-emerald-400" />
                      ) : (
                        <XCircle className="h-10 w-10 shrink-0 text-red-400" />
                      )}
                      <div className="min-w-0 flex-1">
                        <h2 className="text-lg font-bold text-white">
                          {isApproved ? "Approval recorded" : "Plan rejected"}
                        </h2>
                        <p className="mt-1 text-sm text-slate-400">
                          {isApproved
                            ? "Harness continues in the background — open logs for progress."
                            : "Rejected — start a new run or update the project to try again."}
                        </p>
                        <div className="mt-4 flex flex-wrap gap-3">
                          <Link href={`/logs?run=${activeRun}`} className="btn-cyan text-sm">
                            View run logs <ArrowRight className="h-4 w-4" />
                          </Link>
                          <Link
                            href={`/memory?run=${activeRun}`}
                            className="text-sm text-harness-cyan hover:underline"
                          >
                            Memory
                          </Link>
                        </div>
                      </div>
                    </div>
                  </div>

                  {runStage === "awaiting_approval" && (
                    <ApprovalActionBar
                      onApprove={handleApprove}
                      onReject={handleReject}
                      loading={loading}
                      className="mb-6"
                    />
                  )}

                  <ApprovalDocumentPanel
                    docs={docs}
                    activeDoc={activeDoc}
                    onActiveDoc={setActiveDoc}
                    onUpdateDoc={updateDoc}
                    readOnly
                  />
                </>
              )}

              {!pending && !resolved && !showActions && !debateInProgress && (
                <Card>
                  <p className="text-sm text-slate-400">
                    Harness is working (stage:{" "}
                    <span className="font-mono text-harness-cyan">{runStage || "…"}</span>). Open{" "}
                    <Link href={`/logs?run=${activeRun}`} className="text-harness-cyan underline">
                      run logs
                    </Link>{" "}
                    — Approve / Reject appear when debate finishes and status is{" "}
                    <span className="text-amber-300">awaiting_approval</span>.
                  </p>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default function ApprovalPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading…</div>}>
      <ApprovalContent />
    </Suspense>
  );
}

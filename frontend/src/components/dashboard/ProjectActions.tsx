"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Download, Github, Rocket, RefreshCw, FileText } from "lucide-react";
import {
  publishGitHub,
  publishDeploy,
  downloadProjectZipUrl,
  updateProjectRun,
  updateProjectRunWithBrief,
} from "@/lib/api";
import type { HarnessProject } from "@/store/harnessStore";
import { useHarnessStore } from "@/store/harnessStore";
import { isDeployInProgress } from "@/lib/runStage";

type Props = {
  project: HarnessProject;
  stage?: string;
  updateOpen: boolean;
  onUpdateOpenChange: (open: boolean) => void;
  onAction?: () => void;
  endSlot?: React.ReactNode;
};

export function ProjectActions({
  project,
  stage,
  updateOpen,
  onUpdateOpenChange,
  onAction,
  endSlot,
}: Props) {
  const router = useRouter();
  const updateProject = useHarnessStore((s) => s.updateProject);
  const setRunId = useHarnessStore((s) => s.setRunId);
  const clearLogs = useHarnessStore((s) => s.clearLogs);
  const [busy, setBusy] = useState<string | null>(null);
  const [updateText, setUpdateText] = useState("");
  const [updateBrief, setUpdateBrief] = useState<File | null>(null);

  const deployLocked = isDeployInProgress(stage, project.deployUrl) || !!busy;
  const isUpdating =
    project.phase === "UPDATE" ||
    stage === "planning" ||
    stage === "debate" ||
    stage === "building" ||
    stage === "validating" ||
    stage === "awaiting_approval";
  const canPublish =
    !isUpdating &&
    (stage === "ready_to_publish" || stage === "complete" || project.status === "live");
  const showGithub = canPublish && !project.githubUrl && !deployLocked;
  const showDeploy = canPublish && !project.deployUrl && !deployLocked;
  const canDownload =
    project.status === "live" || stage === "ready_to_publish" || stage === "complete";
  const canUpdate =
    (project.status === "live" || stage === "complete" || stage === "ready_to_publish") &&
    !isUpdating;

  const canSubmitUpdate = Boolean(updateText.trim() || updateBrief);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    try {
      await fn();
      onAction?.();
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <div
        className="mt-4 space-y-3 border-t border-harness-border/80 pt-4"
        onClick={(e) => e.preventDefault()}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
            {isUpdating && (
              <span className="text-[10px] font-semibold uppercase tracking-wide text-amber-300 animate-pulse">
                Updating…
              </span>
            )}
            {canDownload && (
              <a
                href={downloadProjectZipUrl(project.id)}
                className="inline-flex items-center gap-1 rounded border border-harness-border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-300 hover:border-harness-cyan/50 hover:text-harness-cyan"
                onClick={(e) => e.stopPropagation()}
              >
                <Download className="h-3 w-3" />
                ZIP
              </a>
            )}
            {deployLocked && (stage === "deploying" || stage === "publishing_github") && (
              <span className="text-[10px] font-semibold uppercase tracking-wide text-amber-300/90 animate-pulse">
                Deploying…
              </span>
            )}
            {showGithub && (
              <button
                type="button"
                disabled={deployLocked}
                onClick={(e) => {
                  e.stopPropagation();
                  run("gh", async () => {
                    updateProject(project.id, { phase: "GITHUB", progress: 92 });
                    const r = await publishGitHub(project.id);
                    if (r.ok && r.github_url) {
                      updateProject(project.id, {
                        githubUrl: r.github_url,
                        phase: "READY",
                        progress: 90,
                      });
                    } else {
                      alert(r.error || "GitHub failed");
                    }
                  });
                }}
                className="inline-flex items-center gap-1 rounded border border-harness-border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-300 hover:border-harness-cyan/50 hover:text-harness-cyan disabled:opacity-50"
              >
                <Github className="h-3 w-3" />
                {busy === "gh" ? "…" : "GitHub"}
              </button>
            )}
            {showDeploy && (
              <button
                type="button"
                disabled={deployLocked}
                onClick={(e) => {
                  e.stopPropagation();
                  run("dep", async () => {
                    updateProject(project.id, { phase: "VERCEL", progress: 95 });
                    const r = await publishDeploy(project.id);
                    if (r.ok && r.deploy_url) {
                      updateProject(project.id, {
                        deployUrl: r.deploy_url,
                        status: "live",
                        phase: "DONE",
                        progress: 100,
                      });
                    } else {
                      alert(r.error || "Deploy failed");
                    }
                  });
                }}
                className="inline-flex items-center gap-1 rounded border border-emerald-500/40 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-400 hover:bg-emerald-500/10 disabled:opacity-50"
              >
                <Rocket className="h-3 w-3" />
                {busy === "dep" ? "…" : "Deploy"}
              </button>
            )}
            {canUpdate && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onUpdateOpenChange(!updateOpen);
                }}
                className={
                  updateOpen
                    ? "inline-flex items-center gap-1 rounded border border-amber-400/60 bg-amber-500/15 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-200"
                    : "inline-flex items-center gap-1 rounded border border-amber-500/40 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-300 hover:bg-amber-500/10"
                }
              >
                <RefreshCw className="h-3 w-3" />
                Update
              </button>
            )}
          </div>
          {endSlot ? <div className="shrink-0 self-center">{endSlot}</div> : null}
        </div>
      </div>

      {updateOpen && (
        <div
          className="absolute left-0 right-0 top-full z-30 mt-2 rounded-lg border border-amber-500/40 bg-harness-surface p-4 shadow-xl shadow-black/40"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="mb-2 text-[11px] text-slate-400">
            Typed notes and/or a Word (.docx) brief — harness re-plans, debates, and rebuilds.
          </p>
          <textarea
            className="mb-2 w-full rounded border border-harness-border bg-harness-bg px-3 py-2 text-xs text-slate-200"
            rows={3}
            value={updateText}
            onChange={(e) => setUpdateText(e.target.value)}
            placeholder="Optional notes on top of your document…"
          />
          <label className="mb-3 flex cursor-pointer items-center gap-2 rounded border border-dashed border-harness-border/80 px-3 py-2 text-xs text-slate-400 hover:border-harness-cyan/40">
            <FileText className="h-3.5 w-3.5 shrink-0 text-harness-cyan" />
            <span className="min-w-0 flex-1 truncate">
              {updateBrief ? updateBrief.name : "Attach Word brief (.docx)"}
            </span>
            <input
              type="file"
              accept=".docx"
              className="sr-only"
              onChange={(e) => setUpdateBrief(e.target.files?.[0] || null)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!!busy || !canSubmitUpdate}
              className="btn-cyan text-xs py-1.5"
              onClick={() =>
                run("upd", async () => {
                  setRunId(project.id);
                  clearLogs();
                  updateProject(project.id, {
                    status: "building",
                    phase: "UPDATE",
                    progress: 18,
                  });
                  if (updateBrief) {
                    await updateProjectRunWithBrief(
                      project.id,
                      updateText.trim(),
                      updateBrief
                    );
                  } else {
                    await updateProjectRun(project.id, updateText.trim());
                  }
                  onUpdateOpenChange(false);
                  setUpdateText("");
                  setUpdateBrief(null);
                  router.push(`/logs?run=${project.id}`);
                })
              }
            >
              {busy === "upd" ? "Starting…" : "Run update"}
            </button>
            <button
              type="button"
              className="rounded border border-harness-border px-3 py-1.5 text-xs text-slate-400 hover:text-white"
              onClick={() => onUpdateOpenChange(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  );
}

"use client";

import Link from "next/link";
import { Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import type { HarnessProject, ProjectStatus } from "@/store/harnessStore";
import { useHarnessStore } from "@/store/harnessStore";
import { deleteRun, getRun } from "@/lib/api";
import { closeHarnessSocket } from "@/hooks/useHarnessSocket";
import { projectPatchFromStage } from "@/lib/runStage";
import { ProjectActions } from "./ProjectActions";

function StatusBadge({
  status,
  phase,
}: {
  status: ProjectStatus;
  phase: string;
}) {
  if (phase === "UPDATE" || status === "planning") {
    return <span className="badge-building shrink-0 animate-pulse">Updating</span>;
  }
  if (status === "live" && phase === "DONE") {
    return <span className="badge-live shrink-0">Live</span>;
  }
  if (status === "awaiting") {
    return <span className="badge-awaiting shrink-0 animate-pulse">Needs approval</span>;
  }
  if (status === "building") {
    return <span className="badge-building shrink-0">Building</span>;
  }
  return <span className="badge-awaiting shrink-0">Failed</span>;
}

type Props = {
  project: HarnessProject;
  updatePanelOpen: boolean;
  onUpdatePanelOpenChange: (open: boolean) => void;
};

export function ProjectCard({ project, updatePanelOpen, onUpdatePanelOpenChange }: Props) {
  const removeProject = useHarnessStore((s) => s.removeProject);
  const updateProject = useHarnessStore((s) => s.updateProject);
  const [deleting, setDeleting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [stage, setStage] = useState<string>("");

  useEffect(() => {
    const sync = () =>
      getRun(project.id)
        .then((d) => {
          setStage(d.stage);
          const gh = d.context?.github_url || "";
          const dep = d.context?.deploy_url || "";
          updateProject(
            project.id,
            projectPatchFromStage(d.stage, {
              approvalStatus: d.approval?.status,
              githubUrl: gh || project.githubUrl,
              deployUrl: dep || project.deployUrl,
              projectMode: d.project_mode,
            })
          );
        })
        .catch(() => {});
    sync();
    const fast = project.phase === "UPDATE" || stage === "planning";
    const interval = setInterval(sync, fast ? 3000 : 6000);
    return () => clearInterval(interval);
  }, [project.id, project.phase, stage, project.githubUrl, project.deployUrl, updateProject]);

  const href =
    project.status === "awaiting"
      ? `/approval?run=${project.id}`
      : project.phase === "DEBATE"
        ? `/debate?run=${project.id}`
        : `/logs?run=${project.id}`;

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirmOpen) {
      setConfirmOpen(true);
      return;
    }
    setDeleting(true);
    try {
      await deleteRun(project.id);
      closeHarnessSocket(project.id);
      removeProject(project.id);
    } catch {
      removeProject(project.id);
    } finally {
      setDeleting(false);
      setConfirmOpen(false);
    }
  };

  const handleCancelConfirm = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setConfirmOpen(false);
  };

  const title =
    project.title.length > 36 ? project.title.slice(0, 36) + "…" : project.title;

  return (
    <article
      className={cn(
        "stat-card relative flex h-[220px] flex-col overflow-visible p-5 transition",
        project.status === "awaiting"
          ? "project-card-awaiting"
          : "hover:border-harness-cyan/30",
        updatePanelOpen && "z-20 ring-1 ring-amber-500/40"
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <Link href={href} className="min-w-0 flex-1">
          <h3 className="truncate font-semibold capitalize text-white hover:text-harness-cyan">
            {title}
          </h3>
          <p className="mt-1 font-mono text-[10px] text-harness-muted">run {project.id}</p>
        </Link>
        <StatusBadge status={project.status} phase={project.phase} />
      </div>

      <Link href={href} className="mb-3 block min-h-[2.5rem] flex-1">
        {stage === "ready_to_publish" ? (
          <p className="text-[11px] font-medium text-amber-300/90">Ready to publish</p>
        ) : project.phase === "BRIEF" ? (
          <p className="text-[11px] text-slate-500">From Word brief</p>
        ) : (
          <p className="text-[11px] text-slate-600">Harness pipeline</p>
        )}
      </Link>

      <div className="mt-auto shrink-0">
        <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-harness-border">
          <div
            className="h-full rounded-full bg-harness-cyan transition-all duration-500"
            style={{ width: `${Math.min(100, project.progress)}%` }}
          />
        </div>
        <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-harness-muted">
          <span className="truncate">{project.phase}</span>
          <span className="shrink-0 text-harness-cyan">{project.progress}%</span>
        </div>
      </div>

      <ProjectActions
        project={project}
        stage={stage}
        updateOpen={updatePanelOpen}
        onUpdateOpenChange={onUpdatePanelOpenChange}
        onAction={() => getRun(project.id).then((d) => setStage(d.stage)).catch(() => {})}
        endSlot={
          confirmOpen ? (
            <div className="flex gap-1">
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="rounded bg-red-600 px-2 py-1 text-[10px] font-bold uppercase text-white"
              >
                {deleting ? "…" : "Confirm"}
              </button>
              <button
                type="button"
                onClick={handleCancelConfirm}
                className="rounded border border-harness-border bg-harness-card px-2 py-1 text-[10px] text-slate-400"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleDelete}
              title="Delete project"
              className="rounded p-1.5 text-slate-500 hover:bg-red-500/20 hover:text-red-400"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )
        }
      />
    </article>
  );
}

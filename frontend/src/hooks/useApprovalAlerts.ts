"use client";

import { useEffect } from "react";
import { getRun } from "@/lib/api";
import { projectPatchFromStage } from "@/lib/runStage";
import { useHarnessStore } from "@/store/harnessStore";

/** Keeps project status in sync when runs are awaiting human approval. */
export function useApprovalAlerts() {
  const projects = useHarnessStore((s) => s.projects);
  const updateProject = useHarnessStore((s) => s.updateProject);

  useEffect(() => {
    if (!projects.length) return;

    const sync = async () => {
      for (const p of projects) {
        try {
          const data = await getRun(p.id);
          const stage = data.stage || "";
          const approval =
            stage === "awaiting_approval" ? "pending" : data.approval?.status || "";
          if (stage === "awaiting_approval" || approval === "pending") {
            updateProject(
              p.id,
              projectPatchFromStage(stage, {
                approvalStatus: approval,
                githubUrl: data.context?.github_url,
                deployUrl: data.context?.deploy_url,
                projectMode: data.project_mode,
              })
            );
          }
        } catch {
          /* backend offline */
        }
      }
    };

    sync();
    const interval = setInterval(sync, 8000);
    return () => clearInterval(interval);
  }, [projects.map((p) => p.id).join(","), updateProject]);
}

export function useNeedsApproval(): {
  needsApproval: boolean;
  firstAwaitingRunId: string | null;
  awaitingCount: number;
} {
  const projects = useHarnessStore((s) => s.projects);
  const awaiting = projects.filter(
    (p) => p.status === "awaiting" || p.phase === "APPROVAL"
  );
  return {
    needsApproval: awaiting.length > 0,
    firstAwaitingRunId: awaiting[0]?.id ?? null,
    awaitingCount: awaiting.length,
  };
}

"use client";

import { useEffect } from "react";
import { getDeployments, getRun } from "@/lib/api";
import { projectPatchFromStage } from "@/lib/runStage";
import { useHarnessStore } from "@/store/harnessStore";

/** Sync GitHub / Vercel URLs and stage from backend into project cards. */
export function useSyncDeployments(enabled = true) {
  useEffect(() => {
    if (!enabled) return;

    const sync = async () => {
      const { projects, updateProject, addProject } = useHarnessStore.getState();
      try {
        const { deployments } = await getDeployments();
        for (const d of deployments) {
          const existing = projects.find((p) => p.id === d.run_id);
          const effectiveStage =
            d.deploy_url && d.stage === "deploying" ? "complete" : d.stage;
          const patch = projectPatchFromStage(effectiveStage, {
            githubUrl: d.github_url || existing?.githubUrl,
            deployUrl: d.deploy_url || existing?.deployUrl,
            projectMode: effectiveStage === "planning" ? "update" : undefined,
          });
          if (existing) {
            updateProject(d.run_id, patch);
          } else if (d.github_url || d.deploy_url || effectiveStage === "complete") {
            addProject({
              id: d.run_id,
              title: d.title.slice(0, 48).toLowerCase(),
              description: "",
              createdAt: new Date().toISOString(),
              ...patch,
              status: patch.status || "building",
              phase: patch.phase || "DONE",
              progress: patch.progress ?? 100,
              githubUrl: d.github_url,
              deployUrl: d.deploy_url,
            });
          }
        }
      } catch {
        for (const p of projects) {
          try {
            const data = await getRun(p.id);
            const gh = data.context?.github_url || "";
            const dep = data.context?.deploy_url || "";
            updateProject(
              p.id,
              projectPatchFromStage(data.stage, {
                approvalStatus: data.approval?.status,
                githubUrl: gh || p.githubUrl,
                deployUrl: dep || p.deployUrl,
                projectMode: data.project_mode,
              })
            );
          } catch {
            /* offline */
          }
        }
      }
    };

    sync();
    const interval = setInterval(sync, 6000);
    return () => clearInterval(interval);
  }, [enabled]);
}

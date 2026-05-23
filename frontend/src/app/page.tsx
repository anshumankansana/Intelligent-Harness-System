"use client";

import Link from "next/link";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatBar } from "@/components/dashboard/StatBar";
import { RecentProjectsList } from "@/components/dashboard/RecentProjectsList";
import { ProjectCard } from "@/components/dashboard/ProjectCard";
import { useHarnessStore } from "@/store/harnessStore";
import { useHarnessSocket } from "@/hooks/useHarnessSocket";
import { useSyncDeployments } from "@/hooks/useSyncDeployments";
import { useEffect, useState } from "react";
import { getRun } from "@/lib/api";
import { projectPatchFromStage } from "@/lib/runStage";

export default function DashboardPage() {
  const { runId, projects, setUrls, updateProject } = useHarnessStore();
  const [updatePanelRunId, setUpdatePanelRunId] = useState<string | null>(null);
  useHarnessSocket(runId);
  useSyncDeployments(projects.length > 0);

  const projectIds = projects.map((p) => p.id).join(",");

  useEffect(() => {
    if (!projectIds) return;
    const ids = projectIds.split(",").filter(Boolean);
    const poll = async () => {
      const list = useHarnessStore.getState().projects.filter((p) => ids.includes(p.id));
      for (const p of list) {
        try {
          const data = await getRun(p.id);
          const gh = data.context?.github_url || "";
          const dep = data.context?.deploy_url || "";
          const stage = data.stage || "";
          const patch = projectPatchFromStage(stage, {
            approvalStatus: data.approval?.status,
            githubUrl: gh || p.githubUrl,
            deployUrl: dep || p.deployUrl,
            projectMode: data.project_mode,
          });
          updateProject(p.id, patch);
          if (stage === "complete" && p.id === runId) setUrls(gh, dep);
        } catch {
          /* backend offline */
        }
      }
    };
    poll();
    const interval = setInterval(poll, 8000);
    return () => clearInterval(interval);
  }, [projectIds, runId, setUrls, updateProject]);

  return (
    <div className="min-h-screen pb-10">
      <PageHeader
        title="IHS Dashboard"
        description="Autonomous engineering intelligence. Plan, debate, build, test — publish when you choose."
      />
      <StatBar projects={projects} />

      <section className="px-8 pb-6">
        <p className="section-label mb-4">Projects</p>

        {projects.length === 0 ? (
          <div className="stat-card flex flex-col items-center justify-center px-8 py-16 text-center">
            <p className="mb-2 text-lg font-medium text-white">No projects yet</p>
            <p className="mb-6 max-w-md text-sm leading-relaxed text-slate-400">
              Start a new idea or import an existing zip. The harness plans, debates, and builds —
              you approve before publish.
            </p>
            <Link href="/new" className="btn-cyan">
              Get started
            </Link>
          </div>
        ) : (
          <div className="grid auto-rows-[220px] gap-5 overflow-visible sm:grid-cols-2 xl:grid-cols-3">
            {projects.map((p) => (
              <ProjectCard
                key={p.id}
                project={p}
                updatePanelOpen={updatePanelRunId === p.id}
                onUpdatePanelOpenChange={(open) =>
                  setUpdatePanelRunId(open ? p.id : null)
                }
              />
            ))}
          </div>
        )}
      </section>

      <RecentProjectsList projects={projects} />
    </div>
  );
}

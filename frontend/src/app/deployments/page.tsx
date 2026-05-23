"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/PageHeader";
import { useHarnessStore } from "@/store/harnessStore";
import { useSyncDeployments } from "@/hooks/useSyncDeployments";
import { getDeployments, getRun, redeployRun, type DeploymentRecord } from "@/lib/api";
import { isDeployInProgress } from "@/lib/runStage";
import { ExternalLink, Rocket, Github, RefreshCw } from "lucide-react";

export default function DeploymentsPage() {
  const { projects, updateProject } = useHarnessStore();
  const [deployments, setDeployments] = useState<DeploymentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [redeploying, setRedeploying] = useState<string | null>(null);
  const [deployingRunIds, setDeployingRunIds] = useState<Set<string>>(new Set());
  const [redeployError, setRedeployError] = useState<string | null>(null);

  useSyncDeployments(true);

  const load = useCallback(async () => {
    try {
      const data = await getDeployments();
      setDeployments(data.deployments || []);
    } catch {
      setDeployments(
        projects
          .filter((p) => p.githubUrl || p.deployUrl || p.status === "live")
          .map((p) => ({
            run_id: p.id,
            title: p.title,
            stage: p.phase === "DONE" ? "complete" : p.phase.toLowerCase(),
            github_url: p.githubUrl || "",
            deploy_url: p.deployUrl || "",
            user_idea: p.description,
          }))
      );
    } finally {
      setLoading(false);
    }
  }, [projects]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  /** Poll API stages so redeploy stays locked until backend leaves `deploying` */
  useEffect(() => {
    const ids = deployments.map((d) => d.run_id);
    if (!ids.length && !redeploying) return;

    const pollStages = async () => {
      const inFlight = new Set<string>();
      const check = redeploying ? [redeploying, ...ids] : ids;
      const unique = Array.from(new Set(check));

      for (const runId of unique) {
        try {
          const run = await getRun(runId);
          const dep = run.context?.deploy_url || "";
          if (isDeployInProgress(run.stage, dep)) {
            inFlight.add(runId);
          }
        } catch {
          if (redeploying === runId) inFlight.add(runId);
        }
      }
      setDeployingRunIds(inFlight);
    };

    pollStages();
    const interval = setInterval(pollStages, 3000);
    return () => clearInterval(interval);
  }, [deployments, redeploying]);

  const deployBusy = redeploying !== null || deployingRunIds.size > 0;

  const handleRedeploy = async (runId: string) => {
    if (deployBusy) return;
    setRedeploying(runId);
    setDeployingRunIds((prev) => new Set(prev).add(runId));
    setRedeployError(null);
    updateProject(runId, { phase: "VERCEL", progress: 95, status: "building" });
    try {
      const result = await redeployRun(runId);
      if (result.ok && result.deploy_url) {
        updateProject(runId, { deployUrl: result.deploy_url, status: "live", phase: "DONE" });
        await load();
      } else {
        setRedeployError(result.error || "Redeploy failed");
      }
    } catch (e) {
      setRedeployError(String(e));
    } finally {
      setRedeploying(null);
      setDeployingRunIds((prev) => {
        const next = new Set(prev);
        next.delete(runId);
        return next;
      });
    }
  };

  const hasUrls = deployments.some((d) => d.github_url || d.deploy_url);
  const hasStub = deployments.some((d) => d.deploy_stub);

  return (
    <>
      <PageHeader
        eyebrow="// DEPLOYMENTS"
        title="Deployments"
        description="GitHub pushes and real Vercel production URLs from completed harness runs."
        showNewProject={false}
      />

      <div className="px-8 py-6">
        {deployBusy && (
          <div className="mb-4 rounded border border-harness-cyan/40 bg-harness-cyan/10 px-4 py-3 text-sm text-cyan-100">
            Deployment in progress — redeploy buttons stay disabled until Vercel finishes (check{" "}
            <Link
              href={`/logs?run=${redeploying || Array.from(deployingRunIds)[0] || ""}`}
              className="underline"
            >
              run logs
            </Link>
            ). Large builds can take several minutes after npm finishes.
          </div>
        )}
        {hasStub && (
          <div className="mb-4 rounded border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            A previous run saved a placeholder Vercel URL (not a real deployment). Click{" "}
            <strong>Redeploy to Vercel</strong> below to publish a working live site.
          </div>
        )}
        {redeployError && (
          <div className="mb-4 rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {redeployError}
          </div>
        )}

        {loading && deployments.length === 0 ? (
          <div className="panel px-8 py-12 text-center text-slate-400">
            <p className="text-sm">Loading deployments…</p>
          </div>
        ) : deployments.length === 0 ? (
          <div className="panel px-8 py-12 text-center text-slate-400">
            <Rocket className="mx-auto mb-3 h-8 w-8 text-harness-muted" />
            <p className="text-sm">No completed runs found yet.</p>
            <p className="mt-2 text-xs text-slate-500">
              Finish a harness run with <code className="text-harness-cyan">GITHUB_TOKEN</code> and{" "}
              <code className="text-harness-cyan">VERCEL_TOKEN</code> in backend{" "}
              <code className="text-harness-cyan">.env</code> to push and deploy.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {!hasUrls && (
              <p className="mb-4 text-sm text-amber-200/90">
                Runs completed locally but no GitHub/Vercel URLs were saved — check tokens in backend{" "}
                <code className="text-harness-cyan">.env</code>.
              </p>
            )}
            {deployments.map((d) => {
              const thisBusy =
                redeploying === d.run_id ||
                (deployingRunIds.has(d.run_id) && !d.deploy_url) ||
                (deployBusy && !d.deploy_url);
              return (
                <div
                  key={d.run_id}
                  className="panel flex flex-wrap items-center justify-between gap-4 p-5 border-emerald-500/20"
                >
                  <div className="min-w-0">
                    <p className="font-semibold capitalize text-white">{d.title}</p>
                    <p className="font-mono text-[10px] text-harness-muted">run {d.run_id}</p>
                    {d.stage === "complete" && (
                      <span className="badge-live mt-2 inline-block">Complete</span>
                    )}
                    {(redeploying === d.run_id ||
                      (deployingRunIds.has(d.run_id) && !d.deploy_url)) && (
                      <span className="badge-building mt-2 ml-2 inline-block animate-pulse">
                        Deploying…
                      </span>
                    )}
                    {d.deploy_url && d.stage === "complete" && (
                      <span className="badge-live mt-2 ml-2 inline-block">Live</span>
                    )}
                    {d.deploy_stub && (
                      <span className="ml-2 mt-2 inline-block rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-300">
                        Placeholder URL (404)
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-sm">
                    {d.github_url ? (
                      <a
                        href={d.github_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-harness-cyan hover:underline"
                      >
                        <Github className="h-4 w-4" />
                        GitHub <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-xs text-slate-500">No GitHub URL</span>
                    )}
                    {d.deploy_url ? (
                      <a
                        href={d.deploy_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-harness-green hover:underline"
                      >
                        <Rocket className="h-4 w-4" />
                        Live URL <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-xs text-slate-500">
                        {d.deploy_stub ? "No live deploy yet" : "No deploy URL"}
                      </span>
                    )}
                    {(d.deploy_stub || (!d.deploy_url && d.github_url)) && (
                      <button
                        type="button"
                        onClick={() => handleRedeploy(d.run_id)}
                        disabled={thisBusy}
                        className="inline-flex items-center gap-1.5 rounded border border-harness-cyan/40 bg-harness-cyan/10 px-3 py-1.5 text-xs font-semibold uppercase text-harness-cyan hover:bg-harness-cyan/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <RefreshCw
                          className={`h-3.5 w-3.5 ${redeploying === d.run_id ? "animate-spin" : ""}`}
                        />
                        {redeploying === d.run_id || deployingRunIds.has(d.run_id)
                          ? "Deploying…"
                          : deployBusy
                            ? "Deploy in progress…"
                            : "Redeploy to Vercel"}
                      </button>
                    )}
                    <Link
                      href={`/logs?run=${d.run_id}`}
                      className="text-xs text-slate-400 hover:text-white"
                    >
                      Logs →
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}

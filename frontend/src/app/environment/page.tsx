"use client";

import { useCallback, useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Input } from "@/components/ui/card";
import { useHarnessStore, type ProviderName } from "@/store/harnessStore";
import {
  getProviderStatus,
  getEnvRequirements,
  getRunEnv,
  saveRunEnv,
  syncProviderKeys,
  syncDeployTokens,
  type EnvRequirement,
  type ProviderStatus,
} from "@/lib/api";
import { API_URL } from "@/lib/utils";
import { cn } from "@/lib/utils";
import Link from "next/link";

function EnvironmentContent() {
  const searchParams = useSearchParams();
  const runParam = searchParams.get("run");
  const {
    providerKeys,
    setProviderKeys,
    deployTokens,
    setDeployTokens,
    envConfigMode,
    setEnvConfigMode,
    projects,
    runId,
    setRunId,
  } = useHarnessStore();

  const activeRun = runParam || runId || projects[0]?.id || "";
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [requirements, setRequirements] = useState<EnvRequirement[]>([]);
  const [projectEnv, setProjectEnv] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const [harnessSaved, setHarnessSaved] = useState(false);
  const [deploySaved, setDeploySaved] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      const st = await getProviderStatus();
      setProviderStatus(st);
    } catch {
      setProviderStatus(null);
    }
  }, []);

  const loadProjectEnv = useCallback(async () => {
    if (!activeRun) {
      setRequirements([]);
      setProjectEnv({});
      return;
    }
    try {
      const [reqRes, envRes] = await Promise.all([
        getEnvRequirements(activeRun),
        getRunEnv(activeRun),
      ]);
      setRequirements(reqRes.requirements || []);
      setProjectEnv((prev) => {
        const merged: Record<string, string> = {};
        for (const r of reqRes.requirements || []) {
          merged[r.key] = prev[r.key] ?? "";
        }
        for (const key of envRes.raw_keys || []) {
          if (!(key in merged)) merged[key] = prev[key] ?? "";
        }
        return merged;
      });
    } catch {
      setRequirements([]);
    }
  }, [activeRun]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (runParam) setRunId(runParam);
  }, [runParam, setRunId]);

  useEffect(() => {
    loadProjectEnv();
  }, [loadProjectEnv]);

  const handleSaveHarness = async () => {
    setLoading(true);
    try {
      if (envConfigMode === "browser") {
        await syncProviderKeys(
          {
            groq: providerKeys.groq,
            gemini: providerKeys.gemini,
            openrouter: providerKeys.openrouter,
          },
          providerKeys.defaultProvider
        );
      }
      setHarnessSaved(true);
      await loadStatus();
      setTimeout(() => setHarnessSaved(false), 2000);
    } catch {
      /* offline */
    }
    setLoading(false);
  };

  const handleSaveDeployTokens = async () => {
    if (!deployTokens.github && !deployTokens.vercel) return;
    setLoading(true);
    try {
      await syncDeployTokens({
        github_token: deployTokens.github,
        vercel_token: deployTokens.vercel,
        vercel_scope: deployTokens.vercelScope,
      });
      setDeploySaved(true);
      await loadStatus();
      setTimeout(() => setDeploySaved(false), 2000);
    } catch {
      alert(
        `Could not sync deploy tokens to ${API_URL}. Check NEXT_PUBLIC_API_URL on Vercel.`
      );
    }
    setLoading(false);
  };

  const handleSaveProjectEnv = async (useDemo = false) => {
    if (!activeRun) return;
    setLoading(true);
    try {
      const payload = { ...projectEnv };
      if (useDemo) {
        for (const r of requirements) {
          if (r.demo_value) payload[r.key] = r.demo_value;
        }
      }
      await saveRunEnv(activeRun, payload, useDemo);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      /* */
    }
    setLoading(false);
  };

  const fillDemoValues = () => {
    const next: Record<string, string> = { ...projectEnv };
    for (const r of requirements) {
      if (r.demo_value) next[r.key] = r.demo_value;
    }
    setProjectEnv(next);
  };

  const backendReady = providerStatus?.backend_env_ready;
  const browserMode = envConfigMode === "browser";

  return (
    <>
      <PageHeader
        eyebrow="// ENVIRONMENT"
        title="API Keys & Environment"
        description="Harness LLM keys (server .env or browser) and per-project secrets for deployed apps."
        showNewProject={false}
      />

      <div className="mx-auto max-w-2xl space-y-6 px-8 py-6">
        <Card title="// Harness AI providers">
          <p className="mb-4 text-sm text-slate-400">
            The harness needs at least one LLM provider. Use{" "}
            <strong className="text-white">backend .env</strong> (recommended for deploy) or paste
            keys here to sync to the server session.
          </p>

          <div className="mb-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setEnvConfigMode("backend")}
              className={cn(
                "rounded border px-3 py-1.5 text-xs font-semibold uppercase",
                !browserMode
                  ? "border-harness-cyan bg-harness-cyan/15 text-harness-cyan"
                  : "border-harness-border text-slate-500"
              )}
            >
              Backend .env
            </button>
            <button
              type="button"
              onClick={() => setEnvConfigMode("browser")}
              className={cn(
                "rounded border px-3 py-1.5 text-xs font-semibold uppercase",
                browserMode
                  ? "border-harness-cyan bg-harness-cyan/15 text-harness-cyan"
                  : "border-harness-border text-slate-500"
              )}
            >
              Browser keys
            </button>
          </div>

          {providerStatus && (
            <div className="mb-4 rounded border border-harness-border/60 bg-black/20 px-3 py-2 text-xs text-slate-400">
              Server:{" "}
              {providerStatus.configured.length
                ? providerStatus.configured.join(", ")
                : "no keys in backend .env"}{" "}
              · GitHub {providerStatus.github ? "✓" : "—"} · Vercel{" "}
              {providerStatus.vercel ? "✓" : "—"}
              {providerStatus.git_available === false && (
                <span className="text-amber-400"> · git missing on server</span>
              )}
            </div>
          )}
          <p className="mb-4 text-xs text-slate-500">
            API: <code className="text-harness-cyan">{API_URL}</code>
          </p>

          {!browserMode && (
            <p className="mb-4 rounded border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
              {backendReady
                ? "Backend .env has provider keys — new runs use the server without pasting keys in the browser."
                : "Add GROQ_API_KEY, GEMINI_API_KEY, or OPENROUTER_API_KEY to backend/.env, then restart uvicorn."}
            </p>
          )}

          {browserMode && (
            <div className="space-y-3">
              <Input
                type="password"
                placeholder="GROQ_API_KEY"
                value={providerKeys.groq}
                onChange={(e) => setProviderKeys({ groq: e.target.value })}
              />
              <Input
                type="password"
                placeholder="GEMINI_API_KEY"
                value={providerKeys.gemini}
                onChange={(e) => setProviderKeys({ gemini: e.target.value })}
              />
              <Input
                type="password"
                placeholder="OPENROUTER_API_KEY"
                value={providerKeys.openrouter}
                onChange={(e) => setProviderKeys({ openrouter: e.target.value })}
              />
              <select
                className="w-full rounded border border-harness-border bg-harness-bg px-4 py-2.5 text-sm"
                value={providerKeys.defaultProvider}
                onChange={(e) =>
                  setProviderKeys({ defaultProvider: e.target.value as ProviderName })
                }
              >
                <option value="groq">Groq — fast</option>
                <option value="gemini">Gemini — planner</option>
                <option value="openrouter">OpenRouter — fallback</option>
              </select>
            </div>
          )}

          <button
            type="button"
            onClick={handleSaveHarness}
            disabled={loading}
            className="btn-cyan mt-4"
          >
            {harnessSaved ? "Saved" : browserMode ? "Sync keys to server" : "Refresh status"}
          </button>
          <p className="mt-2 text-xs text-harness-muted">
            Keys synced to the server stay in memory only — not written to disk. For production,
            use backend/.env on Render.
          </p>
        </Card>

        <Card title="// GitHub & Vercel (publish)">
          <p className="mb-4 text-sm text-slate-400">
            <strong className="text-white">GitHub</strong> and <strong className="text-white">Deploy</strong>{" "}
            buttons need tokens on the API server. Add them to Render <code className="text-harness-cyan">.env</code>{" "}
            or paste here to sync for this server session (recommended for demos).
          </p>
          <div className="space-y-3">
            <Input
              type="password"
              placeholder="GITHUB_TOKEN (classic: repo scope)"
              value={deployTokens.github}
              onChange={(e) => setDeployTokens({ github: e.target.value })}
            />
            <Input
              type="password"
              placeholder="VERCEL_TOKEN"
              value={deployTokens.vercel}
              onChange={(e) => setDeployTokens({ vercel: e.target.value })}
            />
            <Input
              placeholder="VERCEL_SCOPE (team slug, optional)"
              value={deployTokens.vercelScope}
              onChange={(e) => setDeployTokens({ vercelScope: e.target.value })}
            />
          </div>
          <button
            type="button"
            onClick={handleSaveDeployTokens}
            disabled={loading || (!deployTokens.github && !deployTokens.vercel)}
            className="btn-cyan mt-4"
          >
            {deploySaved ? "Saved" : "Sync publish tokens to server"}
          </button>
          {!providerStatus?.github && (
            <p className="mt-2 text-xs text-amber-200/90">
              GitHub publish will fail until a token is configured (server shows —).
            </p>
          )}
        </Card>

        <Card title="// Project environment (deployed app)">
          <p className="mb-4 text-sm text-slate-400">
            Variables detected from the generated app (.env.example, source). Saved on the server per
            run and pushed to <strong className="text-white">Vercel</strong> on deploy.
          </p>

          {projects.length > 0 && (
            <label className="mb-4 block text-xs text-slate-500">
              Project run
              <select
                className="mt-1 w-full rounded border border-harness-border bg-harness-bg px-3 py-2 text-sm text-white"
                value={activeRun}
                onChange={(e) => setRunId(e.target.value)}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title} ({p.id})
                  </option>
                ))}
              </select>
            </label>
          )}

          {!activeRun && (
            <p className="text-sm text-slate-500">Start a project from the dashboard first.</p>
          )}

          {activeRun && requirements.length === 0 && (
            <p className="text-sm text-slate-500">
              No env vars detected yet — build the app first, or add a{" "}
              <code className="text-harness-cyan">.env.example</code> in your import.
            </p>
          )}

          {requirements.length > 0 && (
            <div className="space-y-3">
              {requirements.map((r) => (
                <div key={r.key}>
                  <label className="text-xs font-mono text-harness-cyan">
                    {r.key}
                    {r.required && <span className="text-red-400"> *</span>}
                  </label>
                  <p className="text-[10px] text-slate-500">{r.description}</p>
                  <Input
                    type="password"
                    className="mt-1"
                    placeholder={r.demo_value || `Enter ${r.key}`}
                    value={projectEnv[r.key] || ""}
                    onChange={(e) =>
                      setProjectEnv((prev) => ({ ...prev, [r.key]: e.target.value }))
                    }
                  />
                </div>
              ))}
              <div className="flex flex-wrap gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => handleSaveProjectEnv(false)}
                  disabled={loading}
                  className="btn-cyan text-sm"
                >
                  {saved ? "Saved" : "Save project env"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    fillDemoValues();
                    void handleSaveProjectEnv(true);
                  }}
                  disabled={loading}
                  className="rounded border border-harness-border px-4 py-2 text-sm text-slate-300 hover:bg-white/5"
                >
                  Use demo placeholders
                </button>
              </div>
            </div>
          )}

          {activeRun && (
            <p className="mt-4 text-xs text-harness-muted">
              <Link href={`/deployments`} className="text-harness-cyan underline">
                Deployments
              </Link>{" "}
              — redeploy after saving env so Vercel receives updated secrets.
            </p>
          )}
        </Card>
      </div>
    </>
  );
}

export default function EnvironmentPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading…</div>}>
      <EnvironmentContent />
    </Suspense>
  );
}

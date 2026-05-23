import { create } from "zustand";
import { persist } from "zustand/middleware";
import { shouldAdvancePhase } from "@/lib/runStage";

export type ProviderName = "groq" | "gemini" | "openrouter";
export type ProjectStatus = "live" | "awaiting" | "building" | "planning" | "failed";

export type ProjectMode = "new" | "import" | "update";

export interface HarnessProject {
  id: string;
  title: string;
  description: string;
  status: ProjectStatus;
  phase: string;
  progress: number;
  githubUrl?: string;
  deployUrl?: string;
  createdAt: string;
  projectMode?: ProjectMode;
}

interface ProviderKeys {
  groq: string;
  gemini: string;
  openrouter: string;
  defaultProvider: ProviderName;
}

interface DeployTokens {
  github: string;
  vercel: string;
  vercelScope: string;
}

/** When true, harness uses backend .env only — browser does not send LLM keys */
export type EnvConfigMode = "browser" | "backend";

interface HarnessState {
  runId: string | null;
  userIdea: string;
  logs: string[];
  setLogsForRun: (lines: string[]) => void;
  memoryFiles: Record<string, string>;
  approvalPlan: string;
  approvalStatus: string;
  providerKeys: ProviderKeys;
  deployTokens: DeployTokens;
  envConfigMode: EnvConfigMode;
  githubUrl: string;
  deployUrl: string;
  projects: HarnessProject[];
  setRunId: (id: string | null) => void;
  setUserIdea: (idea: string) => void;
  addLog: (msg: string) => void;
  clearLogs: () => void;
  setMemoryFiles: (files: Record<string, string>) => void;
  setApproval: (plan: string, status: string) => void;
  setProviderKeys: (keys: Partial<ProviderKeys>) => void;
  setDeployTokens: (tokens: Partial<DeployTokens>) => void;
  setEnvConfigMode: (mode: EnvConfigMode) => void;
  setUrls: (github: string, deploy: string) => void;
  addProject: (project: HarnessProject) => void;
  updateProject: (id: string, patch: Partial<HarnessProject>) => void;
  removeProject: (id: string) => void;
  setActiveRun: (runId: string, projectId?: string) => void;
}

export const useHarnessStore = create<HarnessState>()(
  persist(
    (set, get) => ({
      runId: null,
      userIdea: "",
      logs: [],
      setLogsForRun: (lines) => set({ logs: lines }),
      memoryFiles: {},
      approvalPlan: "",
      approvalStatus: "pending",
      providerKeys: {
        groq: "",
        gemini: "",
        openrouter: "",
        defaultProvider: "groq",
      },
      deployTokens: { github: "", vercel: "", vercelScope: "" },
      envConfigMode: "backend",
      githubUrl: "",
      deployUrl: "",
      projects: [],
      setRunId: (runId) => set({ runId }),
      setUserIdea: (userIdea) => set({ userIdea }),
      addLog: (msg) => {
        set((s) => ({ logs: [...s.logs, msg] }));
        const { runId, projects } = get();
        if (!runId) return;
        const p = projects.find((x) => x.id === runId);
        if (!p) return;
        const lower = msg.toLowerCase();
        let patch: Partial<HarnessProject> = {};
        if (lower.includes("update started") || lower.includes("update existing")) {
          patch = { phase: "UPDATE", progress: 18, status: "building" };
        } else if (lower.includes("planner running")) {
          patch = { phase: "PLANNING", progress: 15, status: "planning" };
        } else if (lower.includes("debate chamber") || lower.includes("is speaking")) {
          patch = { phase: "DEBATE", progress: 35, status: "building" };
        } else if (lower.includes("debate complete")) {
          patch = { phase: "APPROVAL", progress: 50, status: "awaiting" };
        } else if (lower.includes("awaiting human approval")) {
          patch = { phase: "APPROVAL", progress: 50, status: "awaiting" };
        } else if (lower.includes("resuming harness") || lower.includes("human approved")) {
          patch = { phase: "DEVELOPMENT", progress: 65, status: "building" };
        } else if (lower.includes("builder engine")) {
          patch = { phase: "DEVELOPMENT", progress: 70, status: "building" };
        } else if (lower.includes("analyzing imported")) {
          patch = { phase: "DEVELOPMENT", progress: 65, status: "building" };
        } else if (lower.includes("validation")) {
          patch = { phase: "VALIDATING", progress: 85, status: "building" };
        } else if (
          lower.includes("build validated") ||
          lower.includes("ready to publish")
        ) {
          patch = { phase: "READY", progress: 90, status: "building" };
        } else if (lower.includes("harness run complete") || lower.includes("github push complete")) {
          patch = { phase: "DONE", progress: 100, status: "live" };
        } else if (lower.includes("harness error")) {
          patch = { phase: "ERROR", progress: 0, status: "failed" };
        }
        if (Object.keys(patch).length && shouldAdvancePhase(p.phase, patch.phase || p.phase)) {
          get().updateProject(runId, patch);
        }
      },
      clearLogs: () => set({ logs: [] }),
      setMemoryFiles: (memoryFiles) => set({ memoryFiles }),
      setApproval: (approvalPlan, approvalStatus) => set({ approvalPlan, approvalStatus }),
      setProviderKeys: (keys) =>
        set((s) => ({ providerKeys: { ...s.providerKeys, ...keys } })),
      setDeployTokens: (tokens) =>
        set((s) => ({ deployTokens: { ...s.deployTokens, ...tokens } })),
      setEnvConfigMode: (envConfigMode) => set({ envConfigMode }),
      setUrls: (githubUrl, deployUrl) => {
        set({ githubUrl, deployUrl });
        const { runId } = get();
        if (runId) {
          get().updateProject(runId, { githubUrl, deployUrl, status: "live", phase: "DONE", progress: 100 });
        }
      },
      addProject: (project) =>
        set((s) => ({ projects: [project, ...s.projects] })),
      updateProject: (id, patch) =>
        set((s) => ({
          projects: s.projects.map((p) => (p.id === id ? { ...p, ...patch } : p)),
        })),
      removeProject: (id) =>
        set((s) => ({
          projects: s.projects.filter((p) => p.id !== id),
          runId: s.runId === id ? null : s.runId,
          logs: s.runId === id ? [] : s.logs,
        })),
      setActiveRun: (runId) => set({ runId }),
    }),
    {
      name: "harness-store",
      partialize: (s) => ({
        providerKeys: s.providerKeys,
        deployTokens: s.deployTokens,
        envConfigMode: s.envConfigMode,
        projects: s.projects,
      }),
    }
  )
);

export function deriveStats(projects: HarnessProject[]) {
  const active = projects.filter(
    (p) => p.status === "building" || p.status === "planning" || p.status === "awaiting"
  ).length;
  const deployed = projects.filter((p) => p.deployUrl || p.status === "live").length;
  return {
    total: projects.length,
    active,
    deployments: deployed,
  };
}

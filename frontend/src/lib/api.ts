import { API_URL } from "./utils";
import type { ProviderName } from "@/store/harnessStore";

export type RunStatus = {
  run_id: string;
  stage: string;
  stage_label: string;
  progress: number;
  error?: string;
  fallback?: {
    pending: boolean;
    failed_provider: string;
    failed_step: string;
    chain: string[];
    message: string;
  };
  next_actions: { label: string; href?: string; action?: string }[];
  memory_files: string[];
  context: {
    user_idea: string;
    approval_status: string;
    github_url?: string;
    deploy_url?: string;
  };
  approval: { status: string; plan_content: string };
  project_mode?: string;
  import_intent?: string;
  project_title?: string;
};

export async function startRun(
  userIdea: string,
  keys: { groq: string; gemini: string; openrouter: string },
  defaultProvider: ProviderName,
  projectTitle?: string
) {
  const res = await fetch(`${API_URL}/api/runs/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_idea: userIdea,
      project_title: projectTitle || "",
      groq_api_key: keys.groq,
      gemini_api_key: keys.gemini,
      openrouter_api_key: keys.openrouter,
      default_provider: defaultProvider,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ run_id: string; project_title?: string }>;
}

export async function startRunWithBrief(
  userIdea: string,
  briefFile: File,
  keys: { groq: string; gemini: string; openrouter: string },
  defaultProvider: ProviderName,
  projectTitle?: string
) {
  const form = new FormData();
  form.append("brief", briefFile);
  form.append("user_idea", userIdea);
  form.append("project_title", projectTitle || "");
  form.append("groq_api_key", keys.groq);
  form.append("gemini_api_key", keys.gemini);
  form.append("openrouter_api_key", keys.openrouter);
  form.append("default_provider", defaultProvider);
  const res = await fetch(`${API_URL}/api/runs/start/brief`, { method: "POST", body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { error?: string }).error || "Failed to start with document");
  return data as {
    run_id: string;
    project_title?: string;
    source_document?: string;
  };
}

export async function getRun(runId: string): Promise<RunStatus> {
  const res = await fetch(`${API_URL}/api/runs/${runId}`);
  return res.json();
}

export type DeploymentRecord = {
  run_id: string;
  title: string;
  stage: string;
  github_url: string;
  deploy_url: string;
  deploy_stub?: boolean;
  user_idea: string;
};

export async function redeployRun(runId: string): Promise<{ ok: boolean; deploy_url?: string; error?: string }> {
  const res = await fetch(`${API_URL}/api/runs/${runId}/redeploy`, { method: "POST" });
  return res.json();
}

export async function getDeployments(): Promise<{ deployments: DeploymentRecord[] }> {
  const res = await fetch(`${API_URL}/api/deployments`);
  if (!res.ok) throw new Error("Failed to load deployments");
  return res.json();
}

export async function deleteRun(runId: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { error?: string }).error || "Delete failed");
  }
  return res.json() as Promise<{ status: string; run_id: string }>;
}

export async function getRunLogs(runId: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/logs`);
  return res.json() as Promise<{ logs: string[] }>;
}

export async function resumeRun(runId: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/resume`, { method: "POST" });
  return res.json();
}

export async function continueFallback(runId: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/continue`, { method: "POST" });
  return res.json();
}

export async function getDebate(runId: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/debate`);
  return res.json() as Promise<{
    transcript: import("@/store/debateStore").DebateMessage[];
    action_items: string[];
    summary: string;
    complete: boolean;
  }>;
}

export async function getMemory(runId: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/memory`);
  return res.json() as Promise<{ files: Record<string, string> }>;
}

export async function submitApproval(
  runId: string,
  action: string,
  humanEdits: string,
  humanInstructions: string,
  importIntent?: string,
  documentEdits?: Record<string, string>,
  documentInstructions?: Record<string, string>
) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action,
      human_edits: humanEdits,
      human_instructions: humanInstructions,
      import_intent: importIntent || "",
      document_edits: documentEdits || {},
      document_instructions: documentInstructions || {},
    }),
  });
  return res.json();
}

export async function importProjectZip(
  file: File,
  title: string,
  description: string
): Promise<{ run_id: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);
  form.append("description", description);
  const res = await fetch(`${API_URL}/api/runs/import`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateProjectRun(runId: string, instructions: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instructions }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateProjectRunWithBrief(
  runId: string,
  instructions: string,
  briefFile: File
) {
  const form = new FormData();
  form.append("brief", briefFile);
  form.append("instructions", instructions);
  const res = await fetch(`${API_URL}/api/runs/${runId}/update/brief`, {
    method: "POST",
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { error?: string }).error || "Update with document failed");
  return data;
}

export async function publishGitHub(runId: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/publish/github`, { method: "POST" });
  return res.json() as Promise<{ ok: boolean; github_url?: string; error?: string }>;
}

export async function publishDeploy(runId: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/publish/deploy`, { method: "POST" });
  return res.json() as Promise<{ ok: boolean; deploy_url?: string; error?: string }>;
}

export function downloadProjectZipUrl(runId: string) {
  return `${API_URL}/api/runs/${runId}/download`;
}

export type ProviderStatus = {
  groq: boolean;
  gemini: boolean;
  openrouter: boolean;
  configured: string[];
  default_provider: string;
  backend_env_ready: boolean;
  github: boolean;
  vercel: boolean;
};

export async function getProviderStatus(): Promise<ProviderStatus> {
  const res = await fetch(`${API_URL}/api/providers/status`);
  if (!res.ok) throw new Error("Failed to load provider status");
  return res.json();
}

export async function syncProviderKeys(
  keys: { groq: string; gemini: string; openrouter: string },
  defaultProvider: ProviderName
) {
  const res = await fetch(`${API_URL}/api/providers/keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      groq_api_key: keys.groq,
      gemini_api_key: keys.gemini,
      openrouter_api_key: keys.openrouter,
      default_provider: defaultProvider,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type EnvRequirement = {
  key: string;
  required: boolean;
  description: string;
  demo_value?: string;
};

export async function getEnvRequirements(runId: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/env-requirements`);
  if (!res.ok) throw new Error("Failed to load env requirements");
  return res.json() as Promise<{ requirements: EnvRequirement[] }>;
}

export async function getRunEnv(runId: string) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/env`);
  if (!res.ok) throw new Error("Failed to load run env");
  return res.json() as Promise<{
    project_env: { values: Record<string, string>; has_values: Record<string, boolean> };
    use_demo_values: boolean;
    raw_keys: string[];
  }>;
}

export async function saveRunEnv(
  runId: string,
  env: Record<string, string>,
  useDemoValues = false
) {
  const res = await fetch(`${API_URL}/api/runs/${runId}/env`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ env, use_demo_values: useDemoValues }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

import type { HarnessProject, ProjectStatus } from "@/store/harnessStore";

/** Ordered pipeline steps shown in the logs sidebar */
export const PIPELINE_STEPS = [
  { key: "planning", label: "Planning" },
  { key: "debate", label: "Agent debate" },
  { key: "awaiting_approval", label: "Human approval" },
  { key: "building", label: "Development" },
  { key: "validating", label: "Validation" },
  { key: "ready_to_publish", label: "Ready to publish" },
  { key: "deploying", label: "Deployment" },
  { key: "complete", label: "Complete" },
] as const;

export const PIPELINE_ORDER = PIPELINE_STEPS.map((s) => s.key);

/** Map backend `stage` to a pipeline step key */
export function pipelineStepKey(stage: string): string {
  const map: Record<string, string> = {
    planning: "planning",
    debate: "debate",
    awaiting_approval: "awaiting_approval",
    approved: "building",
    rejected: "awaiting_approval",
    building: "building",
    validating: "validating",
    validation_failed: "validating",
    awaiting_fallback: "validating",
    ready_to_publish: "ready_to_publish",
    publishing_github: "deploying",
    deploying: "deploying",
    complete: "complete",
    error: "planning",
    unknown: "planning",
  };
  return map[stage] ?? "planning";
}

export function pipelineStepIndex(stage: string): number {
  const key = pipelineStepKey(stage) as (typeof PIPELINE_ORDER)[number];
  const i = PIPELINE_ORDER.indexOf(key);
  return i >= 0 ? i : 0;
}

const PHASE_RANK: Record<string, number> = {
  PLANNING: 10,
  DEBATE: 20,
  APPROVAL: 30,
  APPROVED: 35,
  BUILDING: 40,
  DEVELOPMENT: 40,
  VALIDATING: 50,
  READY: 60,
  GITHUB: 70,
  VERCEL: 75,
  DONE: 100,
  ERROR: 0,
  UPDATE: 15,
  IMPORT: 15,
  REQUIREMENTS: 10,
};

export function shouldAdvancePhase(currentPhase: string, nextPhase: string): boolean {
  const cur = PHASE_RANK[currentPhase] ?? 0;
  const next = PHASE_RANK[nextPhase] ?? 0;
  if (nextPhase === "ERROR") return true;
  if (currentPhase === "ERROR") return next > 0;
  return next >= cur;
}

/** Sync dashboard / logs project card from API stage */
const ACTIVE_STAGES = new Set([
  "planning",
  "debate",
  "awaiting_approval",
  "approved",
  "building",
  "validating",
  "validation_failed",
  "awaiting_fallback",
  "deploying",
  "publishing_github",
  "ready_to_publish",
  "error",
  "rejected",
]);

export function projectPatchFromStage(
  stage: string,
  opts?: {
    approvalStatus?: string;
    githubUrl?: string;
    deployUrl?: string;
    projectMode?: string;
  }
): Partial<HarnessProject> {
  const approval = (opts?.approvalStatus || "").toLowerCase();
  const deployUrl = opts?.deployUrl?.trim() || "";
  const isUpdate = opts?.projectMode === "update";
  const isActive = ACTIVE_STAGES.has(stage);

  if (
    deployUrl &&
    !isActive &&
    (stage === "deploying" || stage === "publishing_github" || stage === "ready_to_publish")
  ) {
    return {
      status: "live" as ProjectStatus,
      phase: "DONE",
      progress: 100,
      githubUrl: opts?.githubUrl,
      deployUrl,
    };
  }

  if (isUpdate && stage === "planning") {
    return {
      status: "building" as ProjectStatus,
      phase: "UPDATE",
      progress: 18,
      githubUrl: opts?.githubUrl,
      deployUrl,
    };
  }

  if (stage === "awaiting_approval" || approval === "pending") {
    return { status: "awaiting" as ProjectStatus, phase: "APPROVAL", progress: 50 };
  }
  if (stage === "rejected") {
    return { status: "failed" as ProjectStatus, phase: "REJECTED", progress: 0 };
  }
  if (stage === "complete") {
    return {
      status: "live" as ProjectStatus,
      phase: "DONE",
      progress: 100,
      githubUrl: opts?.githubUrl,
      deployUrl: opts?.deployUrl || deployUrl,
    };
  }
  if (stage === "error") {
    return { status: "failed" as ProjectStatus, phase: "ERROR", progress: 0 };
  }
  if (stage === "planning") {
    return { status: "planning" as ProjectStatus, phase: "PLANNING", progress: 15 };
  }
  if (stage === "debate") {
    return { status: "building" as ProjectStatus, phase: "DEBATE", progress: 35 };
  }
  if (stage === "approved") {
    return { status: "building" as ProjectStatus, phase: "DEVELOPMENT", progress: 55 };
  }
  if (stage === "building") {
    return { status: "building" as ProjectStatus, phase: "DEVELOPMENT", progress: 70 };
  }
  if (stage === "validating" || stage === "validation_failed" || stage === "awaiting_fallback") {
    return { status: "building" as ProjectStatus, phase: "VALIDATING", progress: 85 };
  }
  if (stage === "ready_to_publish") {
    return {
      status: "building" as ProjectStatus,
      phase: "READY",
      progress: 90,
      githubUrl: opts?.githubUrl,
      deployUrl: opts?.deployUrl,
    };
  }
  if (stage === "publishing_github") {
    return {
      status: "building" as ProjectStatus,
      phase: "GITHUB",
      progress: 92,
      githubUrl: opts?.githubUrl,
    };
  }
  if (stage === "deploying") {
    return {
      status: "building" as ProjectStatus,
      phase: "VERCEL",
      progress: 95,
      deployUrl: opts?.deployUrl,
    };
  }
  return { status: "building" as ProjectStatus, phase: stage.toUpperCase(), progress: 40 };
}

/** Human-readable phase from stage (fallback when store is stale) */
export function phaseLabelFromStage(stage: string): string {
  return projectPatchFromStage(stage).phase || stage.toUpperCase();
}

/** True while GitHub push or Vercel deploy is in progress */
export function isDeployInProgress(stage?: string, deployUrl?: string): boolean {
  if (deployUrl?.trim()) return false;
  return stage === "deploying" || stage === "publishing_github";
}

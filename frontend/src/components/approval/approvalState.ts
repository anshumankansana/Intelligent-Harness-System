/** Shared approval pending / resolved logic for Approval Center */

const PAST_APPROVAL_STAGES = new Set([
  "approved",
  "building",
  "validating",
  "deploying",
  "ready_to_publish",
  "complete",
]);

const PRE_APPROVAL_STAGES = new Set(["planning", "debate", "unknown", ""]);

/** User must act — show Approve / Reject */
export function isPendingApproval(stage: string, approvalStatus: string): boolean {
  if (stage === "awaiting_approval") return true;
  const s = (approvalStatus || "").toLowerCase();
  if (s === "pending") return true;
  return false;
}

/** Already acted or build in progress — hide action buttons */
export function isResolvedApproval(stage: string, approvalStatus: string): boolean {
  if (isPendingApproval(stage, approvalStatus)) return false;

  const s = (approvalStatus || "").toLowerCase();
  if (s === "rejected") return true;

  if (stage === "awaiting_approval") return false;

  // Stale "approved" from a prior cycle while re-planning — not resolved yet
  if (s === "approved" && PRE_APPROVAL_STAGES.has(stage)) {
    return false;
  }

  if (s === "approved" && PAST_APPROVAL_STAGES.has(stage)) {
    return true;
  }

  return PAST_APPROVAL_STAGES.has(stage);
}

export function showApprovalActions(stage: string, approvalStatus: string): boolean {
  return isPendingApproval(stage, approvalStatus);
}

/** Agent debate still running — show wait banner with link to Debate Room */
export function isDebateInProgress(stage: string, debateComplete: boolean): boolean {
  if (debateComplete) return false;
  if (stage === "debate") return true;
  // Debate file not written yet while stage transitions
  if (stage === "planning") return false;
  return false;
}

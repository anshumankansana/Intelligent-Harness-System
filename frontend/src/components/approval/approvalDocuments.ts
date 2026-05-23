/** Memory files shown in Approval Center (order matters). */
export const APPROVAL_DOCUMENTS = [
  { key: "PROJECT_SPEC.md", label: "Project spec" },
  { key: "TASKS.md", label: "Tasks" },
  { key: "ARCHITECTURE.md", label: "Architecture" },
  { key: "DECISIONS.md", label: "Decisions" },
  { key: "RISKS.md", label: "Risks" },
  { key: "TEST_PLAN.md", label: "Test plan" },
  { key: "DEBATE_SUMMARY.md", label: "Debate summary" },
] as const;

export type ApprovalDocKey = (typeof APPROVAL_DOCUMENTS)[number]["key"];

export type DocPanelState = {
  content: string;
  instructions: string;
  view: "read" | "edit";
};

export function emptyDocState(): DocPanelState {
  return { content: "", instructions: "", view: "read" };
}

export function buildDocsFromMemory(
  files: Record<string, string> | undefined
): Record<string, DocPanelState> {
  const out: Record<string, DocPanelState> = {};
  for (const { key } of APPROVAL_DOCUMENTS) {
    out[key] = {
      content: files?.[key] || "",
      instructions: "",
      view: "read",
    };
  }
  return out;
}

export function serializeEdits(docs: Record<string, DocPanelState>): string {
  return APPROVAL_DOCUMENTS.map(({ key, label }) => {
    const c = docs[key]?.content?.trim();
    if (!c) return "";
    return `# ${label}\n\n${c}`;
  })
    .filter(Boolean)
    .join("\n\n---\n\n");
}

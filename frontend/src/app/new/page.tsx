"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/layout/PageHeader";
import { Textarea, Button } from "@/components/ui/card";
import { useHarnessStore } from "@/store/harnessStore";
import { useHarnessSocket } from "@/hooks/useHarnessSocket";
import { startRun, startRunWithBrief, importProjectZip } from "@/lib/api";
import { cn } from "@/lib/utils";
import { FileText } from "lucide-react";

type Tab = "new" | "import";

function slugTitle(title: string, runId: string) {
  const t = title.trim().toLowerCase().slice(0, 48);
  return t || `project-${runId}`;
}

export default function NewProjectPage() {
  const router = useRouter();
  const {
    userIdea,
    setUserIdea,
    setRunId,
    clearLogs,
    providerKeys,
    envConfigMode,
    addProject,
    setActiveRun,
  } = useHarnessStore();
  const [tab, setTab] = useState<Tab>("new");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [importTitle, setImportTitle] = useState("");
  const [importDesc, setImportDesc] = useState("");
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [briefFile, setBriefFile] = useState<File | null>(null);
  useHarnessSocket(null);

  const providerKeysPayload = () =>
    envConfigMode === "browser"
      ? {
          groq: providerKeys.groq,
          gemini: providerKeys.gemini,
          openrouter: providerKeys.openrouter,
        }
      : { groq: "", gemini: "", openrouter: "" };

  const addToStore = (
    run_id: string,
    title: string,
    mode: "new" | "import",
    hasDocument?: boolean
  ) => {
    addProject({
      id: run_id,
      title: slugTitle(title, run_id),
      description: "",
      status: "planning",
      phase: mode === "import" ? "IMPORT" : hasDocument ? "BRIEF" : "REQUIREMENTS",
      progress: 10,
      createdAt: new Date().toISOString(),
      projectMode: mode,
    });
    setRunId(run_id);
    setActiveRun(run_id);
    router.push(mode === "import" ? `/approval?run=${run_id}` : "/");
  };

  const handleStart = async () => {
    const hasText = userIdea.trim().length > 0;
    const hasDoc = Boolean(briefFile);
    if (!hasText && !hasDoc) {
      setError("Describe your project in the box, upload a Word (.docx) brief, or both.");
      return;
    }
    setLoading(true);
    setError("");
    clearLogs();
    try {
      const keys = providerKeysPayload();
      const titleGuess = hasText
        ? userIdea.length > 48
          ? userIdea.slice(0, 48).trim() + "…"
          : userIdea.trim()
        : briefFile?.name.replace(/\.docx$/i, "") || "document-project";

      let run_id: string;
      let project_title = titleGuess;

      if (hasDoc && briefFile) {
        const res = await startRunWithBrief(
          userIdea.trim(),
          briefFile,
          keys,
          providerKeys.defaultProvider,
          titleGuess
        );
        run_id = res.run_id;
        project_title = res.project_title || titleGuess;
      } else {
        const res = await startRun(
          userIdea,
          keys,
          providerKeys.defaultProvider,
          titleGuess
        );
        run_id = res.run_id;
        project_title = res.project_title || titleGuess;
      }

      addToStore(run_id, project_title, "new", hasDoc);
      setBriefFile(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!zipFile) {
      setError("Choose a .zip file of your project.");
      return;
    }
    setLoading(true);
    setError("");
    clearLogs();
    try {
      const title = importTitle.trim() || zipFile.name.replace(/\.zip$/i, "");
      const { run_id } = await importProjectZip(
        zipFile,
        title,
        importDesc.trim() || `Imported: ${title}`
      );
      addToStore(run_id, title, "import");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="// NEW PROJECT"
        title="Launch Harness Run"
        description="Start from typed notes, a Word brief (.docx), or both — or import existing code as a zip."
        showNewProject={false}
      />

      <div className="mx-auto max-w-2xl px-8 py-8">
        <div className="mb-6 flex gap-2 border-b border-harness-border">
          <button
            type="button"
            onClick={() => setTab("new")}
            className={cn(
              "px-4 py-2 text-sm font-medium",
              tab === "new" ? "border-b-2 border-harness-cyan text-harness-cyan" : "text-slate-500"
            )}
          >
            New idea
          </button>
          <button
            type="button"
            onClick={() => setTab("import")}
            className={cn(
              "px-4 py-2 text-sm font-medium",
              tab === "import"
                ? "border-b-2 border-harness-cyan text-harness-cyan"
                : "text-slate-500"
            )}
          >
            Import zip
          </button>
        </div>

        <div className="stat-card p-6">
          {tab === "new" ? (
            <>
              <p className="section-label mb-3">Project brief</p>
              <Textarea
                rows={5}
                placeholder="Optional: extra notes on top of your Word document…"
                value={userIdea}
                onChange={(e) => setUserIdea(e.target.value)}
              />

              <div className="mt-4 rounded border border-dashed border-harness-border/80 bg-black/20 p-4">
                <div className="mb-2 flex items-center gap-2 text-sm text-slate-300">
                  <FileText className="h-4 w-4 text-harness-cyan" />
                  Word document (.docx)
                </div>
                <input
                  type="file"
                  accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  className="block w-full text-sm text-slate-400 file:mr-4 file:rounded file:border-0 file:bg-harness-cyan file:px-4 file:py-2 file:text-xs file:font-bold file:text-black"
                  onChange={(e) => setBriefFile(e.target.files?.[0] || null)}
                />
                {briefFile && (
                  <p className="mt-2 text-xs text-harness-cyan">{briefFile.name}</p>
                )}
                <p className="mt-2 text-xs text-slate-500">
                  Upload a requirements doc — the harness reads it and plans from it. You can also
                  use only the document with no typed text.
                </p>
              </div>

              {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
              <div className="mt-6 flex gap-3">
                <button onClick={handleStart} disabled={loading} className="btn-cyan">
                  {loading ? "Starting…" : "Start harness"}
                </button>
                <Button variant="secondary" onClick={() => router.push("/")}>
                  Cancel
                </Button>
              </div>
            </>
          ) : (
            <>
              <p className="section-label mb-3">Existing project (zip)</p>
              <input
                type="text"
                className="mb-3 w-full rounded border border-harness-border bg-harness-bg px-3 py-2 text-sm text-white"
                placeholder="Project title"
                value={importTitle}
                onChange={(e) => setImportTitle(e.target.value)}
              />
              <Textarea
                rows={2}
                placeholder="Optional notes for the analyzer…"
                value={importDesc}
                onChange={(e) => setImportDesc(e.target.value)}
              />
              <input
                type="file"
                accept=".zip"
                className="mt-4 block w-full text-sm text-slate-400 file:mr-4 file:rounded file:border-0 file:bg-harness-cyan file:px-4 file:py-2 file:text-xs file:font-bold file:text-black"
                onChange={(e) => setZipFile(e.target.files?.[0] || null)}
              />
              <p className="mt-3 text-xs text-slate-500">
                After upload, the harness analyzes architecture and asks for approval: deploy as-is,
                edit then deploy, or continue building.
              </p>
              {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
              <div className="mt-6 flex gap-3">
                <button onClick={handleImport} disabled={loading} className="btn-cyan">
                  {loading ? "Importing…" : "Import & analyze"}
                </button>
                <Button variant="secondary" onClick={() => router.push("/")}>
                  Cancel
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

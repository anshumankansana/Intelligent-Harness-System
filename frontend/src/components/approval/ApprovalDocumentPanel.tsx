"use client";

import { useState } from "react";
import { MemoryDocument } from "@/components/memory/MemoryDocument";
import { Textarea } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  APPROVAL_DOCUMENTS,
  type ApprovalDocKey,
  type DocPanelState,
} from "./approvalDocuments";

type Props = {
  docs: Record<string, DocPanelState>;
  activeDoc: ApprovalDocKey;
  onActiveDoc: (key: ApprovalDocKey) => void;
  onUpdateDoc: (key: ApprovalDocKey, patch: Partial<DocPanelState>) => void;
  disabled?: boolean;
  readOnly?: boolean;
};

export function ApprovalDocumentPanel({
  docs,
  activeDoc,
  onActiveDoc,
  onUpdateDoc,
  disabled,
  readOnly,
}: Props) {
  const current = docs[activeDoc] || { content: "", instructions: "", view: "read" as const };
  const [section, setSection] = useState<"document" | "instructions">("document");
  const locked = Boolean(disabled || readOnly);

  return (
    <div className="overflow-hidden rounded-lg border border-harness-border bg-harness-card/40">
      <div className="flex gap-1 overflow-x-auto border-b border-harness-border bg-harness-bg/60 p-2">
        {APPROVAL_DOCUMENTS.map(({ key, label }) => {
          const hasContent = Boolean(docs[key]?.content?.trim());
          const hasInstr = Boolean(docs[key]?.instructions?.trim());
          return (
            <button
              key={key}
              type="button"
              onClick={() => {
                onActiveDoc(key);
                setSection("document");
              }}
              className={cn(
                "shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition",
                activeDoc === key
                  ? "bg-harness-cyan/15 text-harness-cyan ring-1 ring-harness-cyan/40"
                  : "text-slate-400 hover:bg-white/5 hover:text-white",
                !hasContent && "opacity-60"
              )}
            >
              {label}
              {hasInstr && (
                <span
                  className="ml-1.5 inline-block h-1.5 w-1.5 rounded-full bg-amber-400"
                  title="Has instructions"
                />
              )}
            </button>
          );
        })}
      </div>

      <div className="flex gap-4 border-b border-harness-border/80 px-4">
        <button
          type="button"
          onClick={() => setSection("document")}
          className={cn(
            "py-2.5 text-sm font-medium",
            section === "document"
              ? "border-b-2 border-harness-cyan text-harness-cyan"
              : "text-slate-500 hover:text-slate-300"
          )}
        >
          Document
        </button>
        <button
          type="button"
          onClick={() => setSection("instructions")}
          disabled={locked}
          className={cn(
            "py-2.5 text-sm font-medium",
            section === "instructions"
              ? "border-b-2 border-amber-400 text-amber-300"
              : "text-slate-500 hover:text-slate-300",
            locked && "cursor-default opacity-60"
          )}
        >
          Instructions
          {current.instructions.trim() && (
            <span className="ml-1.5 text-[10px] text-amber-400">●</span>
          )}
        </button>
      </div>

      <div className="p-4">
        {section === "document" ? (
          current.content.trim() ? (
            <div className="max-h-[min(52vh,520px)] overflow-y-auto rounded border border-harness-border/60">
              <MemoryDocument content={current.content} filename={activeDoc} />
            </div>
          ) : (
            <p className="rounded border border-dashed border-harness-border py-12 text-center text-sm text-slate-500">
              No content for this document yet.
            </p>
          )
        ) : (
          <div className="space-y-2">
            <p className="text-xs text-slate-400">
              Optional notes for <span className="text-harness-cyan">{activeDoc}</span> — included
              when you approve the full package.
            </p>
            <Textarea
              rows={10}
              disabled={locked}
              readOnly={readOnly}
              value={current.instructions}
              onChange={(e) => onUpdateDoc(activeDoc, { instructions: e.target.value })}
              placeholder="Constraints or changes for this document…"
            />
          </div>
        )}
      </div>
    </div>
  );
}

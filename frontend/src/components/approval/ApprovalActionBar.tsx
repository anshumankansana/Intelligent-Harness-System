"use client";

import { Button } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Props = {
  onApprove: () => void;
  onReject: () => void;
  loading?: boolean;
  sticky?: boolean;
  className?: string;
};

export function ApprovalActionBar({
  onApprove,
  onReject,
  loading,
  sticky,
  className,
}: Props) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-4 rounded-lg border border-harness-cyan/30 bg-harness-card/95 p-4 shadow-lg backdrop-blur-sm",
        sticky &&
          "sticky bottom-4 z-50 mt-6 border-red-500/40 bg-harness-bg/95 shadow-[0_-8px_32px_rgba(0,0,0,0.45)]",
        className
      )}
    >
      <p className="text-sm text-slate-300">
        <span className="font-semibold text-white">Your decision</span> — approve to continue the
        build, or reject to stop this run.
      </p>
      <div className="flex shrink-0 flex-wrap gap-3">
        <button
          type="button"
          onClick={onApprove}
          disabled={loading}
          className="btn-cyan min-w-[140px] px-6 py-2.5 text-sm font-semibold disabled:opacity-50"
        >
          {loading ? "Submitting…" : "Approve all"}
        </button>
        <Button
          variant="danger"
          onClick={onReject}
          disabled={loading}
          className="min-w-[100px] px-6 py-2.5"
        >
          Reject
        </Button>
      </div>
    </div>
  );
}

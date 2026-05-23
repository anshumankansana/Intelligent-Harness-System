"use client";

import Link from "next/link";
import { MessagesSquare, ArrowRight } from "lucide-react";

type Props = {
  runId: string;
  stage: string;
};

export function DebateWaitingBanner({ runId, stage }: Props) {
  return (
    <div className="mb-6 rounded-lg border border-violet-500/40 bg-violet-500/10 p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-violet-400/50 bg-violet-500/20">
            <MessagesSquare className="h-5 w-5 animate-pulse text-violet-300" />
          </div>
          <div>
            <p className="text-sm font-semibold text-violet-100">Agent debate in progress</p>
            <p className="mt-1 text-sm text-slate-400">
              Engineers are debating the plan
              {stage === "debate" ? " live" : ""}. Approval opens when the moderator finishes and
              status moves to <span className="font-mono text-amber-300">awaiting_approval</span>.
              Please wait — you can watch the conversation in the Debate Room.
            </p>
          </div>
        </div>
        <Link
          href={`/debate?run=${runId}`}
          className="btn-cyan inline-flex shrink-0 items-center justify-center gap-2 text-sm"
        >
          Open Debate Room
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}

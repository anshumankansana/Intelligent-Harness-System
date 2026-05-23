import { Check, Circle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  PIPELINE_STEPS,
  PIPELINE_ORDER,
  pipelineStepIndex,
  pipelineStepKey,
} from "@/lib/runStage";

export function PipelineStepper({ stage, progress }: { stage: string; progress: number }) {
  const currentKey = pipelineStepKey(stage);
  const current = pipelineStepIndex(stage);

  return (
    <div className="stat-card p-4">
      <p className="section-label mb-4">// Pipeline</p>
      <ul className="space-y-0">
        {PIPELINE_STEPS.map((step, i) => {
          const stepIdx = PIPELINE_ORDER.indexOf(step.key);
          const done = current > stepIdx || stage === "complete";
          const isActive =
            currentKey === step.key &&
            stage !== "complete" &&
            stage !== "rejected" &&
            stage !== "error";

          return (
            <li key={step.key} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-full border",
                    done && "border-emerald-500/50 bg-emerald-500/20 text-emerald-400",
                    isActive && !done && "border-harness-cyan bg-harness-cyan/20 text-harness-cyan",
                    !done && !isActive && "border-harness-border text-harness-muted"
                  )}
                >
                  {done ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : isActive ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Circle className="h-3 w-3" />
                  )}
                </div>
                {i < PIPELINE_STEPS.length - 1 && (
                  <div
                    className={cn(
                      "my-0.5 w-px flex-1 min-h-[20px]",
                      done ? "bg-emerald-500/40" : "bg-harness-border"
                    )}
                  />
                )}
              </div>
              <div className="pb-5 pt-0.5">
                <p
                  className={cn(
                    "text-xs font-medium",
                    isActive ? "text-harness-cyan" : done ? "text-slate-300" : "text-harness-muted"
                  )}
                >
                  {step.label}
                </p>
                {isActive && (
                  <p className="text-[10px] text-harness-muted">{progress}% · running</p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

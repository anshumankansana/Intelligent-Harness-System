import { cn } from "@/lib/utils";

function classifyLine(line: string): "info" | "succ" | "warn" | "err" {
  const l = line.toLowerCase();
  if (l.includes("error") || l.includes("failed") || l.includes("harness error")) return "err";
  if (l.includes("warn") || l.includes("fallback") || l.includes("awaiting")) return "warn";
  if (
    l.includes("complete") ||
    l.includes("passed") ||
    l.includes("approved") ||
    l.includes("pushed") ||
    l.includes("saved")
  )
    return "succ";
  return "info";
}

const TAG: Record<string, string> = {
  info: "text-slate-500",
  succ: "text-emerald-500",
  warn: "text-amber-500",
  err: "text-red-500",
};

export function LogTerminal({ lines }: { lines: string[] }) {
  return (
    <div className="log-terminal font-mono text-[13px] leading-relaxed">
      {lines.length === 0 ? (
        <p className="text-harness-muted">Waiting for log output…</p>
      ) : (
        lines.map((line, i) => {
          const kind = classifyLine(line);
          const tag = kind === "succ" ? "SUCC" : kind === "warn" ? "WARN" : kind === "err" ? "ERR" : "INFO";
          return (
            <div key={i} className="log-line flex gap-3 py-1 border-b border-harness-border/30">
              <span className="shrink-0 text-[10px] text-harness-muted/70">
                {String(i + 1).padStart(3, "0")}
              </span>
              <span className={cn("shrink-0 text-[10px] font-bold", TAG[kind])}>[{tag}]</span>
              <span
                className={cn(
                  "min-w-0 break-words",
                  kind === "err" && "text-red-300/90",
                  kind === "warn" && "text-amber-200/80",
                  kind === "succ" && "text-emerald-300/90",
                  kind === "info" && "text-slate-400"
                )}
              >
                {line}
              </span>
            </div>
          );
        })
      )}
    </div>
  );
}

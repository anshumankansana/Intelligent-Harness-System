import { AlertTriangle, Shield, DollarSign, Gauge, TestTube2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DebateMessage } from "@/store/debateStore";

const AGENT_META: Record<string, { icon: typeof Shield; severity: "high" | "medium" | "low"; border: string }> = {
  security: { icon: Shield, severity: "high", border: "border-l-red-500" },
  cost: { icon: DollarSign, severity: "medium", border: "border-l-amber-500" },
  performance: { icon: Gauge, severity: "medium", border: "border-l-amber-500" },
  qa: { icon: TestTube2, severity: "low", border: "border-l-emerald-500" },
  moderator: { icon: AlertTriangle, severity: "low", border: "border-l-harness-cyan" },
};

function agentKey(name: string) {
  const n = name.toLowerCase();
  if (n.includes("security") || n.includes("alex")) return "security";
  if (n.includes("cost") || n.includes("morgan")) return "cost";
  if (n.includes("performance") || n.includes("jordan")) return "performance";
  if (n.includes("qa") || n.includes("sam")) return "qa";
  return "moderator";
}

function severityStyle(s: string) {
  if (s === "high") return "text-red-400 bg-red-500/10 border-red-500/30";
  if (s === "medium") return "text-amber-400 bg-amber-500/10 border-amber-500/30";
  return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30";
}

export function AgentFindingsPanel({
  messages,
  actionItems,
  summary,
}: {
  messages: DebateMessage[];
  actionItems: string[];
  summary?: string;
}) {
  const findings = messages.filter((m) => !m.agent_name.toLowerCase().includes("moderator")).slice(-4);

  return (
    <div className="space-y-4">
      <div className="stat-card p-4">
        <p className="section-label mb-3">// Agent findings</p>
        {findings.length === 0 ? (
          <p className="text-xs text-slate-500">Open Debate Room while agents are speaking.</p>
        ) : (
          <ul className="space-y-3">
            {findings.map((m, i) => {
              const key = agentKey(m.agent_name);
              const meta = AGENT_META[key] || AGENT_META.moderator;
              const Icon = meta.icon;
              const excerpt =
                m.content.length > 160 ? m.content.slice(0, 160).trim() + "…" : m.content;
              return (
                <li
                  key={i}
                  className={cn("agent-finding-card border-l-4 pl-3", meta.border)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Icon className="h-3.5 w-3.5 text-slate-400" />
                      <span className="text-xs font-semibold text-white">{m.agent_name}</span>
                    </div>
                    <span
                      className={cn(
                        "rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase",
                        severityStyle(meta.severity)
                      )}
                    >
                      {meta.severity}
                    </span>
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{excerpt}</p>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {(summary || actionItems.length > 0) && (
        <div className="stat-card border-harness-cyan/20 p-4">
          <p className="section-label mb-2">// Consensus</p>
          {summary ? (
            <p className="text-xs leading-relaxed text-slate-300 line-clamp-6">{summary}</p>
          ) : (
            <ul className="space-y-1.5 text-xs text-slate-400">
              {actionItems.slice(0, 4).map((item, i) => (
                <li key={i} className="flex gap-2">
                  <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-400" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

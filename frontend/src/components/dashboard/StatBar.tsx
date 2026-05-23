import { GitBranch, CheckCircle2, Activity, Rocket } from "lucide-react";
import { deriveStats, type HarnessProject } from "@/store/harnessStore";

export function StatBar({ projects }: { projects: HarnessProject[] }) {
  const stats = deriveStats(projects);
  const passed = projects.filter((p) => p.status === "live").length;

  const items = [
    { label: "Projects run", value: stats.total, icon: GitBranch },
    { label: "Builds passed", value: passed, icon: CheckCircle2 },
    { label: "Active now", value: stats.active, icon: Activity },
    { label: "Deployed", value: stats.deployments, icon: Rocket },
  ];

  return (
    <div className="grid grid-cols-1 divide-y divide-harness-border border-b border-harness-border sm:grid-cols-2 lg:grid-cols-4 lg:divide-x lg:divide-y-0">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <div
            key={item.label}
            className="flex items-center gap-4 px-8 py-5 transition hover:bg-white/[0.02]"
          >
            <Icon className="h-5 w-5 shrink-0 text-harness-muted" />
            <div className="min-w-0">
              <p className="truncate text-[10px] font-semibold uppercase tracking-widest text-harness-muted">
                {item.label}
              </p>
              <p className="text-3xl font-bold tabular-nums text-harness-amber">{item.value}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

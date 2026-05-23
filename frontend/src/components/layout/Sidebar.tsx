"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Plus,
  AlertTriangle,
  Rocket,
  KeyRound,
  Cpu,
  FileCode2,
  CheckSquare,
  MessagesSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApprovalAlerts, useNeedsApproval } from "@/hooks/useApprovalAlerts";

const mainNav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/new", label: "New Project", icon: Plus },
  { href: "/logs", label: "Incidents", icon: AlertTriangle },
  { href: "/deployments", label: "Deployments", icon: Rocket },
  { href: "/environment", label: "Environment", icon: KeyRound },
];

const secondaryNav = [
  { href: "/debate", label: "Debate Room", icon: MessagesSquare },
  { href: "/approval", label: "Approvals", icon: CheckSquare, approvalGate: true },
  { href: "/memory", label: "Memory", icon: FileCode2 },
];

export function Sidebar() {
  const pathname = usePathname();
  useApprovalAlerts();
  const { needsApproval, firstAwaitingRunId, awaitingCount } = useNeedsApproval();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-56 flex-col border-r border-harness-border bg-harness-surface/95 backdrop-blur-md">
      <div className="flex items-center gap-2 border-b border-harness-border px-4 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded border border-harness-cyan/30 bg-harness-cyan/10">
          <Cpu className="h-4 w-4 text-harness-cyan" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight text-white">IHS</p>
          <p className="text-[9px] font-mono uppercase tracking-widest text-harness-muted">
            Harness OS
          </p>
        </div>
      </div>

      {needsApproval && (
        <div className="mx-2 mt-3 rounded border border-red-500/50 bg-red-500/10 px-3 py-2 approval-nav-blink">
          <p className="text-[10px] font-bold uppercase tracking-wider text-red-300">
            Action required
          </p>
          <p className="mt-0.5 text-[10px] text-red-200/80">
            {awaitingCount} project{awaitingCount > 1 ? "s" : ""} need approval
          </p>
        </div>
      )}

      <nav className="flex-1 space-y-1 px-2 py-4">
        {mainNav.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 text-xs font-semibold uppercase tracking-wider transition",
                active
                  ? "border-l-2 border-harness-cyan bg-harness-cyan/10 text-harness-cyan"
                  : "border-l-2 border-transparent text-slate-400 hover:bg-white/5 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}

        <div className="my-4 border-t border-harness-border pt-4">
          <p className="mb-2 px-3 section-label">Workflow</p>
          {secondaryNav.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}?`);
            const Icon = item.icon;
            const isApproval = item.approvalGate;
            const href =
              isApproval && firstAwaitingRunId
                ? `/approval?run=${firstAwaitingRunId}`
                : item.href;
            const blinkApproval = isApproval && needsApproval && !pathname.startsWith("/approval");

            return (
              <Link
                key={item.href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 text-xs font-medium uppercase tracking-wider transition rounded-sm",
                  active && !blinkApproval
                    ? "text-harness-cyan"
                    : blinkApproval
                      ? "approval-nav-blink"
                      : "text-slate-500 hover:text-slate-300"
                )}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <span className="flex-1">{item.label}</span>
                {blinkApproval && awaitingCount > 0 && (
                  <span className="flex h-5 min-w-[20px] shrink-0 items-center justify-center rounded bg-amber-500 px-1.5 text-[10px] font-bold text-black">
                    {awaitingCount}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </nav>

      <div className="border-t border-harness-border p-4">
        <p className="font-mono text-[10px] text-harness-muted">v0.1.0 · hackathon</p>
      </div>
    </aside>
  );
}

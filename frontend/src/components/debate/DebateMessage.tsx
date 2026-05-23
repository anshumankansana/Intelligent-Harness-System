"use client";

import Image from "next/image";
import { avatarUrl } from "@/store/debateStore";
import type { DebateMessage as Msg } from "@/store/debateStore";
import { cn } from "@/lib/utils";

export function DebateMessageBubble({ message }: { message: Msg }) {
  const isMod = message.agent_id === "moderator";

  return (
    <div
      className={cn(
        "flex gap-3 debate-msg-enter",
        isMod && "justify-center"
      )}
    >
      {!isMod && (
        <div
          className="relative h-11 w-11 shrink-0 overflow-hidden rounded-full border-2"
          style={{ borderColor: message.color }}
        >
          <Image
            src={avatarUrl(message.avatar_seed, message.color)}
            alt={message.agent_name}
            width={44}
            height={44}
            className="h-full w-full object-cover bg-slate-800"
            unoptimized
          />
        </div>
      )}
      <div className={cn("max-w-[85%]", isMod && "max-w-[90%] text-center")}>
        {!isMod && (
          <div className="mb-1 flex items-baseline gap-2">
            <span className="text-sm font-semibold text-white">{message.agent_name}</span>
            <span className="text-[10px] uppercase tracking-wider text-harness-muted">
              {message.agent_title}
            </span>
          </div>
        )}
        {isMod && (
          <p className="mb-1 text-[10px] font-mono uppercase tracking-widest text-harness-green">
            Moderator
          </p>
        )}
        <div
          className={cn(
            "rounded-lg px-4 py-3 text-sm leading-relaxed text-slate-200",
            isMod
              ? "border border-harness-green/30 bg-harness-green/10"
              : "border border-harness-border bg-harness-card"
          )}
          style={!isMod ? { borderLeftColor: message.color, borderLeftWidth: 3 } : undefined}
        >
          {message.content}
        </div>
      </div>
    </div>
  );
}

export function TypingIndicator({
  name,
  color,
  seed,
}: {
  name: string;
  color: string;
  seed: string;
}) {
  return (
    <div className="flex gap-3 opacity-80">
      <div
        className="h-11 w-11 shrink-0 overflow-hidden rounded-full border-2"
        style={{ borderColor: color }}
      >
        <Image
          src={avatarUrl(seed, color)}
          alt={name}
          width={44}
          height={44}
          className="h-full w-full"
          unoptimized
        />
      </div>
      <div className="flex items-center gap-2 rounded-lg border border-harness-border bg-harness-card px-4 py-3">
        <span className="text-sm text-slate-400">{name} is thinking</span>
        <span className="flex gap-1">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-harness-cyan [animation-delay:0ms]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-harness-cyan [animation-delay:150ms]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-harness-cyan [animation-delay:300ms]" />
        </span>
      </div>
    </div>
  );
}

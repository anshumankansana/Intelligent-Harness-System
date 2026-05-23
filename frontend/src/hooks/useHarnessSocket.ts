"use client";

import { useEffect, useRef } from "react";
import { useHarnessStore } from "@/store/harnessStore";
import { useDebateStore, type DebateMessage } from "@/store/debateStore";
import { WS_URL } from "@/lib/utils";

const sockets = new Map<string, WebSocket>();

/** One stable WebSocket per runId — logs + live debate events. */
export function useHarnessSocket(runId: string | null) {
  const addLog = useHarnessStore((s) => s.addLog);
  const setAgents = useDebateStore((s) => s.setAgents);
  const addMessage = useDebateStore((s) => s.addMessage);
  const setTyping = useDebateStore((s) => s.setTyping);
  const setComplete = useDebateStore((s) => s.setComplete);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    if (!runId) return;

    useDebateStore.getState().setRunId(runId);

    let ws = sockets.get(runId);
    let created = false;

    if (!ws || ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
      ws = new WebSocket(`${WS_URL}/ws/logs/${runId}`);
      sockets.set(runId, ws);
      created = true;
    }

    const onMessage = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "ping") return;

        if (data.type === "debate") {
          const event = data.event;
          const payload = data.data || {};
          if (event === "debate_start") {
            setAgents(payload.agents || []);
          } else if (event === "debate_typing") {
            setTyping(payload.agent_id || null);
          } else if (event === "debate_message") {
            addMessage(payload as DebateMessage);
          } else if (event === "debate_complete") {
            setComplete(payload.summary || "", payload.action_items || []);
          }
          return;
        }

        if (data.message) addLog(data.message);
      } catch {
        if (ev.data) addLog(String(ev.data));
      }
    };

    const onOpen = () => {
      if (created && mounted.current) {
        addLog("[Connected to live stream]");
      }
      try {
        ws?.send("ping");
      } catch {
        /* ignore */
      }
    };

    ws.addEventListener("message", onMessage);
    ws.addEventListener("open", onOpen);

    const pingIv = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        try {
          ws.send("ping");
        } catch {
          /* ignore */
        }
      }
    }, 25000);

    return () => {
      mounted.current = false;
      clearInterval(pingIv);
      ws?.removeEventListener("message", onMessage);
      ws?.removeEventListener("open", onOpen);
    };
  }, [runId, addLog, setAgents, addMessage, setTyping, setComplete]);
}

export function closeHarnessSocket(runId: string) {
  const ws = sockets.get(runId);
  if (ws) {
    ws.close();
    sockets.delete(runId);
  }
}

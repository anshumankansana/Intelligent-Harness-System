import { create } from "zustand";

export type DebateAgent = {
  id: string;
  name: string;
  title: string;
  color: string;
  avatar_seed: string;
  focus?: string;
};

export type DebateMessage = {
  agent_id: string;
  agent_name: string;
  agent_title: string;
  color: string;
  avatar_seed: string;
  content: string;
  timestamp: string;
  turn_index: number;
};

interface DebateState {
  runId: string | null;
  agents: DebateAgent[];
  messages: DebateMessage[];
  typingAgentId: string | null;
  complete: boolean;
  actionItems: string[];
  summary: string;
  setRunId: (id: string | null) => void;
  reset: () => void;
  setAgents: (agents: DebateAgent[]) => void;
  addMessage: (msg: DebateMessage) => void;
  setTyping: (agentId: string | null) => void;
  setComplete: (summary: string, actionItems: string[]) => void;
  loadFromApi: (data: {
    agents?: DebateAgent[];
    transcript: DebateMessage[];
    action_items: string[];
    summary: string;
    complete: boolean;
  }) => void;
}

export const useDebateStore = create<DebateState>((set) => ({
  runId: null,
  agents: [],
  messages: [],
  typingAgentId: null,
  complete: false,
  actionItems: [],
  summary: "",
  setRunId: (runId) => set({ runId }),
  reset: () =>
    set({
      agents: [],
      messages: [],
      typingAgentId: null,
      complete: false,
      actionItems: [],
      summary: "",
    }),
  setAgents: (agents) => set({ agents }),
  addMessage: (msg) =>
    set((s) => ({
      messages: [...s.messages, msg],
      typingAgentId: null,
    })),
  setTyping: (typingAgentId) => set({ typingAgentId }),
  setComplete: (summary, actionItems) =>
    set({ complete: true, summary, actionItems, typingAgentId: null }),
  loadFromApi: (data) => {
    const fromApi = data.agents?.length ? data.agents : agentsFromTranscript(data.transcript || []);
    set({
      agents: fromApi,
      messages: data.transcript || [],
      actionItems: data.action_items || [],
      summary: data.summary || "",
      complete: data.complete,
      typingAgentId: null,
    });
  },
}));

function agentsFromTranscript(transcript: DebateMessage[]): DebateAgent[] {
  const seen = new Set<string>();
  const out: DebateAgent[] = [];
  for (const m of transcript) {
    if (!m.agent_id || seen.has(m.agent_id)) continue;
    seen.add(m.agent_id);
    out.push({
      id: m.agent_id,
      name: m.agent_name,
      title: m.agent_title,
      color: m.color,
      avatar_seed: m.avatar_seed,
    });
  }
  return out;
}

export function avatarUrl(seed: string, color: string) {
  const bg = color.replace("#", "");
  return `https://api.dicebear.com/7.x/bottts-neutral/svg?seed=${encodeURIComponent(seed)}&backgroundColor=${bg}`;
}

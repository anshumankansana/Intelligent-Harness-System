import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from harness.debate.profiles import DEBATE_AGENTS, MODERATOR, AgentProfile
from harness.providers.base import ProviderRole
from harness.providers.factory import ProviderFactory

LogFn = Callable[[str], Awaitable[None]]
DebateEventFn = Callable[[str, dict], Awaitable[None]]


@dataclass
class DebateTurn:
    agent_id: str
    agent_name: str
    agent_title: str
    color: str
    avatar_seed: str
    content: str
    timestamp: str
    turn_index: int


class DebateSystem:
    """Multi-agent debate as a live conversation with streaming UI events."""

    def __init__(
        self,
        factory: ProviderFactory,
        log: LogFn,
        emit: Optional[DebateEventFn] = None,
        run_id: str = "",
    ):
        self.factory = factory
        self.log = log
        self.emit = emit
        self.run_id = run_id
        self.transcript: List[DebateTurn] = []
        self.action_items: List[str] = []

    async def _event(self, event: str, data: dict) -> None:
        if self.emit:
            await self.emit(event, data)

    async def run(self, architecture: str, run_dir: Optional[Path] = None) -> str:
        await self.log("Debate chamber opening — agents joining...")
        await self._event("debate_start", {"agents": [self._profile_dict(a) for a in DEBATE_AGENTS]})

        # Moderator opens
        opening = await self._moderator_open(architecture)
        await self._add_turn(MODERATOR, opening, 0)

        context = f"Architecture under review:\n{architecture[:4000]}\n\n"
        turn_idx = 1

        for agent in DEBATE_AGENTS:
            await self._event("debate_typing", {"agent_id": agent.id, "agent_name": agent.name})
            await self.log(f"{agent.name} is speaking...")
            await asyncio.sleep(0.8)

            reply = await self._agent_speak(agent, context, self._format_transcript())
            await self._add_turn(agent, reply, turn_idx)
            turn_idx += 1
            context = self._format_transcript()
            await asyncio.sleep(0.5)

        await self.log("Moderator synthesizing debate...")
        await self._event("debate_typing", {"agent_id": MODERATOR.id, "agent_name": MODERATOR.name})
        synthesis = await self._moderator_close(architecture)
        await self._add_turn(MODERATOR, synthesis, turn_idx)

        self.action_items = self._extract_action_items(synthesis)
        summary = self._build_summary_markdown(synthesis)

        await self._event(
            "debate_complete",
            {
                "summary": summary,
                "action_items": self.action_items,
                "transcript": [asdict(t) for t in self.transcript],
            },
        )
        await self.log("Debate complete — review decisions in Debate Room, then approve.")

        if run_dir:
            self._persist(run_dir, summary)

        return summary

    def _profile_dict(self, p: AgentProfile) -> dict:
        return {
            "id": p.id,
            "name": p.name,
            "title": p.title,
            "color": p.color,
            "avatar_seed": p.avatar_seed,
            "focus": p.focus,
        }

    async def _add_turn(self, profile: AgentProfile, content: str, index: int) -> None:
        turn = DebateTurn(
            agent_id=profile.id,
            agent_name=profile.name,
            agent_title=profile.title,
            color=profile.color,
            avatar_seed=profile.avatar_seed,
            content=content.strip(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            turn_index=index,
        )
        self.transcript.append(turn)
        await self._event("debate_message", asdict(turn))

    def _format_transcript(self) -> str:
        lines = []
        for t in self.transcript:
            lines.append(f"**{t.agent_name}** ({t.agent_title}): {t.content}")
        return "\n\n".join(lines)

    async def _agent_speak(self, agent: AgentProfile, architecture: str, thread: str) -> str:
        prompt = f"""You are {agent.name}, the {agent.title} in a LIVE engineering debate.
Personality: {agent.personality}
Your focus: {agent.focus}

Speak in first person. Respond to what others said — agree, disagree, or build on their points.
Keep it conversational (3-5 sentences). No markdown headers.

{architecture[:2000]}

Conversation so far:
{thread[-6000:] if thread else "(opening — you go first after moderator)"}

Your message:"""
        resp = await self.factory.complete_with_fallback(
            prompt,
            f"You are {agent.name}. Debate naturally like a team meeting.",
            role=ProviderRole.FAST,
            log=self.log,
            run_id=self.run_id,
        )
        return resp.content

    async def _moderator_open(self, architecture: str) -> str:
        prompt = f"""You are the Debate Moderator. Open the architecture review session.
Briefly state what will be debated (1-2 sentences). Be professional and welcoming.

Architecture snippet:
{architecture[:1500]}"""
        resp = await self.factory.complete_with_fallback(
            prompt,
            "You are a neutral debate moderator.",
            role=ProviderRole.FAST,
            log=self.log,
            run_id=self.run_id,
        )
        return resp.content

    async def _moderator_close(self, architecture: str) -> str:
        thread = self._format_transcript()
        prompt = f"""You are the Debate Moderator. Synthesize this debate into:
1. Key decisions (bullet list)
2. Action items for the human approver (bullet list, concrete)
3. Open risks to accept or mitigate

Debate transcript:
{thread}

End with: "Human approval required before build phase."
"""
        resp = await self.factory.complete_with_fallback(
            prompt,
            "Synthesize debates clearly.",
            role=ProviderRole.PLANNER,
            log=self.log,
            run_id=self.run_id,
        )
        return resp.content

    def _extract_action_items(self, synthesis: str) -> List[str]:
        items = []
        in_actions = False
        for line in synthesis.splitlines():
            low = line.lower().strip()
            if "action item" in low or "action items" in low:
                in_actions = True
                continue
            if in_actions and line.strip().startswith(("#", "##", "1.", "key decision")):
                if "action" not in line.lower():
                    break
            if in_actions and line.strip().startswith(("-", "*", "•")):
                items.append(line.strip().lstrip("-*• ").strip())
        if not items:
            for line in synthesis.splitlines():
                if line.strip().startswith(("-", "*", "•")):
                    items.append(line.strip().lstrip("-*• ").strip())
        return items[:8]

    def _build_summary_markdown(self, synthesis: str) -> str:
        from harness.memory.formatter import clean_markdown

        lines = []
        for t in self.transcript:
            lines.append(f"## {t.agent_name} — {t.agent_title}")
            lines.append("")
            lines.append(t.content.strip())
            lines.append("")
        transcript_md = "\n".join(lines)
        actions = "\n".join(f"- {a}" for a in self.action_items) or "- See moderator synthesis below."
        raw = f"""# Debate Summary

## Conversation

{transcript_md}

## Moderator synthesis

{synthesis.strip()}

## Action items

{actions}
"""
        return clean_markdown(raw, "DEBATE_SUMMARY.md")

    def _persist(self, run_dir: Path, summary: str) -> None:
        from harness.memory.formatter import wrap_with_template

        mem = run_dir / "memory"
        mem.mkdir(parents=True, exist_ok=True)
        formatted = wrap_with_template("DEBATE_SUMMARY.md", summary)
        (mem / "DEBATE_SUMMARY.md").write_text(formatted, encoding="utf-8")
        (mem / "DEBATE_TRANSCRIPT.json").write_text(
            json.dumps(
                {
                    "transcript": [asdict(t) for t in self.transcript],
                    "action_items": self.action_items,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

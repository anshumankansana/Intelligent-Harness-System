from dataclasses import dataclass
from typing import List


@dataclass
class AgentProfile:
    id: str
    name: str
    title: str
    focus: str
    color: str
    avatar_seed: str
    personality: str


DEBATE_AGENTS: List[AgentProfile] = [
    AgentProfile(
        id="security",
        name="Alex Chen",
        title="Security Agent",
        focus="auth, secrets, injection, OWASP",
        color="#ef4444",
        avatar_seed="alex-security",
        personality="cautious, precise, cites risks clearly",
    ),
    AgentProfile(
        id="cost",
        name="Morgan Blake",
        title="Cost Agent",
        focus="free tier, infra cost, API usage",
        color="#f59e0b",
        avatar_seed="morgan-cost",
        personality="pragmatic, budget-focused, favors free tiers",
    ),
    AgentProfile(
        id="performance",
        name="Jordan Kim",
        title="Performance Agent",
        focus="latency, caching, scalability",
        color="#22d3ee",
        avatar_seed="jordan-perf",
        personality="data-driven, obsessed with speed and scale",
    ),
    AgentProfile(
        id="qa",
        name="Sam Rivera",
        title="QA Agent",
        focus="testability, edge cases, reliability",
        color="#a78bfa",
        avatar_seed="sam-qa",
        personality="skeptical, thinks in test cases and edge cases",
    ),
]

MODERATOR = AgentProfile(
    id="moderator",
    name="IHS Moderator",
    title="Debate Moderator",
    focus="synthesis and action items",
    color="#22c55e",
    avatar_seed="ihs-moderator",
    personality="neutral facilitator",
)

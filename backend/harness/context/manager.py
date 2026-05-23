from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HarnessContext:
    run_id: str
    user_idea: str
    human_edits: str = ""
    human_instructions: str = ""
    approval_status: str = "pending"
    provider_prefs: Dict[str, str] = field(default_factory=dict)
    debate_summary: str = ""
    validation_logs: List[str] = field(default_factory=list)
    retry_count: int = 0
    github_url: str = ""
    deploy_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def inject_human_context(self) -> str:
        parts = [f"User idea: {self.user_idea}"]
        if self.human_edits:
            parts.append(f"Human-edited plan:\n{self.human_edits}")
        if self.human_instructions:
            parts.append(f"Additional instructions:\n{self.human_instructions}")
        if self.debate_summary:
            parts.append(f"Debate tradeoffs:\n{self.debate_summary}")
        return "\n\n".join(parts)

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ApprovalRequest:
    run_id: str
    stage: str
    plan_content: str
    status: str = "pending"
    human_edits: str = ""
    human_instructions: str = ""


class ApprovalGate:
    """Human-in-the-loop approval store (in-memory for MVP)."""

    def __init__(self):
        self._pending: Dict[str, ApprovalRequest] = {}

    def create(self, run_id: str, stage: str, plan_content: str) -> ApprovalRequest:
        req = ApprovalRequest(run_id=run_id, stage=stage, plan_content=plan_content)
        self._pending[run_id] = req
        return req

    def get(self, run_id: str) -> Optional[ApprovalRequest]:
        return self._pending.get(run_id)

    def resolve(
        self,
        run_id: str,
        action: str,
        human_edits: str = "",
        human_instructions: str = "",
    ) -> Optional[ApprovalRequest]:
        req = self._pending.get(run_id)
        if not req:
            return None
        if action in ("approve", "approved"):
            action = "approved"
        elif action in ("reject", "rejected"):
            action = "rejected"
        req.status = action
        req.human_edits = human_edits
        req.human_instructions = human_instructions
        return req

    def is_approved(self, run_id: str) -> bool:
        req = self._pending.get(run_id)
        return req is not None and req.status == "approved"

    def is_rejected(self, run_id: str) -> bool:
        req = self._pending.get(run_id)
        return req is not None and req.status == "rejected"

    def clear(self, run_id: str) -> None:
        self._pending.pop(run_id, None)

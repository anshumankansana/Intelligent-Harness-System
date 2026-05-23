from dataclasses import dataclass
from typing import Dict, List, Optional

# After Gemini fails, user continues with this chain (per user spec)
GEMINI_FAILURE_CHAIN = ["openrouter", "groq"]

# Fast/builder default chain if primary fails
FAST_FAILURE_CHAIN = ["openrouter", "groq", "gemini"]


@dataclass
class FallbackRequest:
    run_id: str
    failed_step: str
    failed_provider: str
    error_message: str
    fallback_chain: List[str]
    status: str = "pending"  # pending | continued | dismissed


class ProviderFallbackGate:
    """Human checkpoint when a provider fails — user clicks Continue to run fallback chain."""

    def __init__(self):
        self._pending: Dict[str, FallbackRequest] = {}

    def create(
        self,
        run_id: str,
        failed_step: str,
        failed_provider: str,
        error_message: str,
        fallback_chain: Optional[List[str]] = None,
    ) -> FallbackRequest:
        chain = fallback_chain or (
            GEMINI_FAILURE_CHAIN if failed_provider == "gemini" else FAST_FAILURE_CHAIN
        )
        req = FallbackRequest(
            run_id=run_id,
            failed_step=failed_step,
            failed_provider=failed_provider,
            error_message=error_message[:500],
            fallback_chain=chain,
        )
        self._pending[run_id] = req
        return req

    def get(self, run_id: str) -> Optional[FallbackRequest]:
        return self._pending.get(run_id)

    def mark_continued(self, run_id: str) -> Optional[FallbackRequest]:
        req = self._pending.get(run_id)
        if req:
            req.status = "continued"
        return req

    def is_continued(self, run_id: str) -> bool:
        req = self._pending.get(run_id)
        return req is not None and req.status == "continued"

    def clear(self, run_id: str) -> None:
        self._pending.pop(run_id, None)

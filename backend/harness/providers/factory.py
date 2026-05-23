import asyncio
import re
from typing import Awaitable, Callable, Dict, List, Optional

from harness.providers.base import BaseLLMProvider, ProviderConfig, ProviderRole, LLMResponse
from harness.providers.gemini_provider import GeminiProvider
from harness.providers.groq_provider import GroqProvider
from harness.providers.model_registry import get_model
from harness.providers.openrouter_provider import OpenRouterProvider

ROLE_TO_CONFIG_KEY = {
    ProviderRole.FAST: "fast",
    ProviderRole.PLANNER: "planner",
    ProviderRole.FALLBACK: "default",
}

PROVIDER_MAP = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
    "openrouter": OpenRouterProvider,
}

ROLE_DEFAULTS: Dict[ProviderRole, str] = {
    ProviderRole.FAST: "groq",
    ProviderRole.PLANNER: "gemini",
    ProviderRole.FALLBACK: "openrouter",
}

ROLE_PROVIDER_ORDER: Dict[ProviderRole, list] = {
    ProviderRole.FAST: ["groq", "openrouter", "gemini"],
    ProviderRole.PLANNER: ["gemini", "openrouter", "groq"],
    ProviderRole.FALLBACK: ["openrouter", "groq", "gemini"],
}

PLANNER_AUTO_CHAIN = ["gemini", "openrouter", "groq"]
FAST_AUTO_CHAIN = ["groq", "openrouter", "gemini"]

LogFn = Optional[Callable[[str], Awaitable[None]]]


class ProviderExhaustedError(Exception):
    def __init__(self, provider: str, step: str, message: str, chain: List[str]):
        self.provider = provider
        self.step = step
        self.chain = chain
        super().__init__(message)


class ProviderFactory:
    def __init__(self, keys: Dict[str, str], default: str = "groq"):
        self.keys = {k: v for k, v in keys.items() if v}
        self.default = default if default in self.keys else next(iter(self.keys), "groq")
        self._force_chain: Dict[str, List[str]] = {}

    def set_fallback_chain(self, run_id: str, chain: List[str]) -> None:
        self._force_chain[run_id] = chain

    def clear_fallback_chain(self, run_id: str) -> None:
        self._force_chain.pop(run_id, None)

    def chain_for_role(self, role: ProviderRole) -> List[str]:
        if role == ProviderRole.PLANNER:
            return [p for p in PLANNER_AUTO_CHAIN if p in self.keys]
        return [p for p in FAST_AUTO_CHAIN if p in self.keys]

    def get(self, name: Optional[str] = None, role: ProviderRole = ProviderRole.FAST) -> BaseLLMProvider:
        provider_name = name or self.default
        if provider_name not in self.keys:
            raise ValueError(f"No API key for provider: {provider_name}")
        cls = PROVIDER_MAP.get(provider_name)
        if not cls:
            raise ValueError(f"Unknown provider: {provider_name}")
        role_key = ROLE_TO_CONFIG_KEY[role]
        model = get_model(provider_name, role_key)
        provider = cls(ProviderConfig(api_key=self.keys[provider_name], model=model))
        provider.role = role_key  # type: ignore[attr-defined]
        return provider

    def get_for_role(self, role: ProviderRole) -> BaseLLMProvider:
        for name in ROLE_PROVIDER_ORDER.get(role, ["groq", "gemini", "openrouter"]):
            if name in self.keys:
                return self.get(name, role=role)
        raise ValueError("No providers configured")

    async def complete_primary_only(
        self, prompt: str, system: str = "", role: ProviderRole = ProviderRole.FAST
    ) -> LLMResponse:
        """Deprecated: use complete_with_fallback for automatic provider rotation."""
        return await self.complete_with_fallback(prompt, system, role)

    def _fallback_chain_for_role(self, role: ProviderRole, skip: str = "") -> List[str]:
        full = PLANNER_AUTO_CHAIN if role == ProviderRole.PLANNER else FAST_AUTO_CHAIN
        if skip:
            return [p for p in full if p != skip and p in self.keys]
        return [p for p in full if p in self.keys]

    async def complete_with_chain(
        self,
        prompt: str,
        system: str,
        role: ProviderRole,
        chain: List[str],
        run_id: str = "",
        log: LogFn = None,
    ) -> LLMResponse:
        if run_id and run_id in self._force_chain:
            chain = self._force_chain[run_id]
        chain = [p for p in chain if p in self.keys]
        if not chain:
            raise ProviderExhaustedError(
                "none",
                "",
                "No API keys configured for fallback chain",
                self._fallback_chain_for_role(role),
            )

        last_error: Exception | None = None
        for i, name in enumerate(chain):
            try:
                if log:
                    await log(f"Trying {name} ({role.value})...")
                provider = self.get(name, role=role)
                resp = await provider.complete(prompt, system)
                resp.provider = name  # type: ignore[attr-defined]
                if log and i > 0:
                    await log(f"Fallback succeeded with {name} ({resp.model})")
                elif log:
                    await log(f"Using {name} ({resp.model})")
                return resp
            except Exception as e:
                last_error = e
                err_text = str(e)
                if log:
                    hint = "rate limited — " if re.search(r"\b429\b", err_text) else ""
                    await log(
                        f"{name} failed: {hint}{err_text[:200]} — "
                        + ("trying next provider..." if i < len(chain) - 1 else "no more providers.")
                    )
                if i < len(chain) - 1 and re.search(r"\b429\b", err_text):
                    await asyncio.sleep(1.5)
                continue

        primary = chain[0]
        raise ProviderExhaustedError(
            primary,
            "",
            str(last_error or "All providers in chain failed"),
            chain[1:],
        )

    async def complete_with_fallback(
        self,
        prompt: str,
        system: str = "",
        role: ProviderRole = ProviderRole.FAST,
        log: LogFn = None,
        run_id: str = "",
    ) -> LLMResponse:
        """Try each provider for the role in order until one succeeds (fully automatic)."""
        if role == ProviderRole.PLANNER:
            order = PLANNER_AUTO_CHAIN
        elif role == ProviderRole.FAST:
            order = FAST_AUTO_CHAIN
        else:
            order = ["openrouter", "groq", "gemini"]
        return await self.complete_with_chain(prompt, system, role, order, run_id=run_id, log=log)

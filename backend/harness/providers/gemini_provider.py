import asyncio

import httpx

from harness.providers.base import BaseLLMProvider, LLMResponse, ProviderConfig
from harness.providers.model_registry import get_model


class GeminiProvider(BaseLLMProvider):
    name = "gemini"
    role: str = "planner"

    @property
    def default_model(self) -> str:
        return get_model("gemini", self.role)

    def _url(self) -> str:
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.config.api_key}"
        )

    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        last_err: Exception | None = None

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    resp = await client.post(
                        self._url(),
                        json={
                            "contents": [{"parts": [{"text": full_prompt}]}],
                            "generationConfig": {
                                "temperature": 0.4,
                                "maxOutputTokens": 4096,
                            },
                        },
                    )
                    if resp.status_code in (429, 503, 500):
                        await asyncio.sleep(2 ** attempt)
                        last_err = RuntimeError(f"Gemini HTTP {resp.status_code}")
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates") or []
                    if not candidates:
                        raise ValueError("Gemini returned no candidates")
                    parts = candidates[0].get("content", {}).get("parts") or []
                    if not parts:
                        raise ValueError("Gemini returned empty content")
                    text = parts[0].get("text", "")
                    if not text.strip():
                        raise ValueError("Gemini returned blank text")
                    return LLMResponse(content=text, provider=self.name, model=self.model)
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code in (429, 503, 500):
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except Exception as e:
                last_err = e
                await asyncio.sleep(1)
        raise last_err or RuntimeError("Gemini request failed")

import asyncio

import httpx

from harness.providers.base import BaseLLMProvider, LLMResponse, ProviderConfig
from harness.providers.model_registry import get_model


class OpenRouterProvider(BaseLLMProvider):
    name = "openrouter"
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    role: str = "fast"

    @property
    def default_model(self) -> str:
        return get_model("openrouter", self.role)

    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(
                        self.BASE_URL,
                        headers={
                            "Authorization": f"Bearer {self.config.api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://intelligent-harness.local",
                            "X-Title": "Intelligent Harness System",
                        },
                        json={
                            "model": self.model,
                            "messages": messages,
                            "temperature": 0.3,
                        },
                    )
                    if resp.status_code in (429, 503, 500):
                        await asyncio.sleep(2 ** attempt)
                        last_err = RuntimeError(f"OpenRouter HTTP {resp.status_code}")
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return LLMResponse(content=content, provider=self.name, model=self.model)
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code in (429, 503, 500):
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except Exception as e:
                last_err = e
                await asyncio.sleep(1)
        raise last_err or RuntimeError("OpenRouter request failed")

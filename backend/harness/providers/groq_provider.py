import asyncio

import httpx

from harness.providers.base import BaseLLMProvider, LLMResponse, ProviderConfig
from harness.providers.model_registry import get_model


class GroqProvider(BaseLLMProvider):
    name = "groq"
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    role: str = "fast"

    @property
    def default_model(self) -> str:
        return get_model("groq", self.role)

    async def complete(self, prompt: str, system: str = "") -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_err: Exception | None = None
        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(
                        self.BASE_URL,
                        headers={
                            "Authorization": f"Bearer {self.config.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "messages": messages,
                            "temperature": 0.3,
                            "max_tokens": 8192,
                        },
                    )
                    if resp.status_code in (429, 503, 500):
                        wait = min(8, 2 ** attempt)
                        last_err = RuntimeError(f"Groq HTTP {resp.status_code} (rate limit)")
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return LLMResponse(content=content, provider=self.name, model=self.model)
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code in (429, 503, 500):
                    await asyncio.sleep(min(8, 2 ** attempt))
                    continue
                raise
            except Exception as e:
                last_err = e
                await asyncio.sleep(1)
        raise last_err or RuntimeError("Groq request failed after retries")

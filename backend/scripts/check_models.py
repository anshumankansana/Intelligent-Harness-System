#!/usr/bin/env python3
"""
Probe Groq, Gemini, and OpenRouter with your API keys.
Picks the best working FREE models and writes harness/providers/selected_models.json.

Usage (from backend/):
  python scripts/check_models.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# backend root on path
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")

import httpx

from harness.providers.model_candidates import ALL_CANDIDATES
from harness.providers.model_registry import FALLBACK_MODELS, save_registry

PING_PROMPT = "Reply with exactly: OK"
PING_SYSTEM = "You are a connectivity test. One word only."


async def test_groq(client: httpx.AsyncClient, api_key: str, model: str) -> tuple[bool, str]:
    try:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": PING_PROMPT}],
                "max_tokens": 16,
                "temperature": 0,
            },
            timeout=45.0,
        )
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"]
            return True, text[:40]
        return False, f"HTTP {r.status_code}: {r.text[:120]}"
    except Exception as e:
        return False, str(e)[:120]


async def test_openrouter(client: httpx.AsyncClient, api_key: str, model: str) -> tuple[bool, str]:
    try:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://intelligent-harness.local",
                "X-Title": "IHS Model Check",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": PING_SYSTEM},
                    {"role": "user", "content": PING_PROMPT},
                ],
                "max_tokens": 16,
                "temperature": 0,
            },
            timeout=60.0,
        )
        if r.status_code == 200:
            data = r.json()
            choices = data.get("choices") or []
            if not choices:
                return False, "empty choices"
            msg = choices[0].get("message") or {}
            text = msg.get("content") or ""
            return True, (text[:40] if text else "ok")
        return False, f"HTTP {r.status_code}: {r.text[:120]}"
    except Exception as e:
        return False, str(e)[:120]


async def test_gemini(client: httpx.AsyncClient, api_key: str, model: str) -> tuple[bool, str]:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    try:
        r = await client.post(
            url,
            json={
                "contents": [{"parts": [{"text": PING_PROMPT}]}],
                "generationConfig": {"maxOutputTokens": 16, "temperature": 0},
            },
            timeout=45.0,
        )
        if r.status_code == 200:
            parts = r.json()["candidates"][0]["content"]["parts"]
            return True, parts[0]["text"][:40]
        return False, f"HTTP {r.status_code}: {r.text[:120]}"
    except Exception as e:
        return False, str(e)[:120]


async def pick_first(
    client: httpx.AsyncClient,
    provider: str,
    api_key: str,
    role: str,
    tester,
) -> tuple[str | None, list[dict]]:
    results = []
    chosen = None
    candidates = ALL_CANDIDATES[provider].get(role) or ALL_CANDIDATES[provider]["default"]
    for model in candidates:
        ok, detail = await tester(client, api_key, model)
        results.append({"model": model, "ok": ok, "detail": detail})
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {provider}/{role}: {model} — {detail}")
        if ok and chosen is None:
            chosen = model
        await asyncio.sleep(0.3)
    return chosen, results


async def list_groq_models(client: httpx.AsyncClient, api_key: str) -> list[str]:
    try:
        r = await client.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20.0,
        )
        if r.status_code == 200:
            return sorted(m["id"] for m in r.json().get("data", []))
    except Exception:
        pass
    return []


async def main() -> int:
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    or_key = os.getenv("OPENROUTER_API_KEY", "").strip()

    print("=" * 60)
    print("Intelligent Harness — FREE model verification")
    print("=" * 60)

    selected: dict[str, str] = {}
    report: dict = {}

    async with httpx.AsyncClient() as client:
        if groq_key:
            print("\n[Groq] Available models from API:")
            available = await list_groq_models(client, groq_key)
            if available:
                print("  " + ", ".join(available[:12]) + ("..." if len(available) > 12 else ""))
            else:
                print("  (could not list — probing candidates only)")

            print("\n[Groq] Probing candidates...")
            for role in ("fast", "planner"):
                m, res = await pick_first(client, "groq", groq_key, role, test_groq)
                report[f"groq_{role}"] = res
                if m:
                    selected[f"groq_{role}"] = m
            if "groq_fast" in selected:
                selected["groq"] = selected["groq_fast"]
        else:
            print("\n[Groq] SKIP — no GROQ_API_KEY in backend/.env")

        if gemini_key:
            print("\n[Gemini] Probing free-tier candidates...")
            for role in ("planner", "fast"):
                m, res = await pick_first(client, "gemini", gemini_key, role, test_gemini)
                report[f"gemini_{role}"] = res
                if m:
                    selected[f"gemini_{role}"] = m
            if "gemini_planner" in selected:
                selected["gemini"] = selected["gemini_planner"]
        else:
            print("\n[Gemini] SKIP — no GEMINI_API_KEY in backend/.env")

        if or_key:
            print("\n[OpenRouter] Probing :free candidates...")
            for role in ("planner", "fast", "default"):
                m, res = await pick_first(client, "openrouter", or_key, role, test_openrouter)
                report[f"openrouter_{role}"] = res
                if m:
                    selected[f"openrouter_{role}"] = m
            if "openrouter_fast" in selected:
                selected["openrouter"] = selected["openrouter_fast"]
            if selected.get("openrouter"):
                selected["openrouter_fallback"] = selected.get(
                    "openrouter_default", selected["openrouter"]
                )
        else:
            print("\n[OpenRouter] SKIP — no OPENROUTER_API_KEY in backend/.env")

    # If Gemini failed all probes, route planner to Groq
    if gemini_key and not selected.get("gemini_planner"):
        print("\n[Gemini] No working model — planner will use Groq (gpt-oss-120b or llama-3.3).")
    if groq_key and selected.get("groq_fast") and not selected.get("groq_planner"):
        selected["groq_planner"] = selected.get("groq_fast")

    # Merge fallbacks for missing providers
    for k, v in FALLBACK_MODELS.items():
        if k not in selected:
            selected[k] = v

    if selected.get("openrouter_default") and not selected.get("openrouter"):
        selected["openrouter"] = selected["openrouter_default"]
        selected["openrouter_fast"] = selected.get("openrouter_fast") or selected["openrouter_default"]
        selected["openrouter_planner"] = selected.get("openrouter_planner") or selected["openrouter_default"]

    path = save_registry(selected)
    print("\n" + "=" * 60)
    print("SELECTED MODELS (written to selected_models.json)")
    print("=" * 60)
    for provider in ("groq", "gemini", "openrouter"):
        val = selected.get(provider, FALLBACK_MODELS.get(provider, "-"))
        print(f"  {provider:12} -> {val}")
    print(f"  groq fast    -> {selected.get('groq_fast', '-')}")
    print(f"  groq planner -> {selected.get('groq_planner', selected.get('groq', '-'))}")
    print(f"  gemini plan  -> {selected.get('gemini_planner', '-')}")
    print(f"  OR fast      -> {selected.get('openrouter_fast', '-')}")
    print(f"  OR planner   -> {selected.get('openrouter_planner', '-')}")
    print(f"\nSaved: {path}")

    any_ok = any(
        selected.get(p) and selected.get(p) != FALLBACK_MODELS.get(p)
        for p in ("groq", "gemini", "openrouter")
    ) or bool(selected.get("groq_fast") or selected.get("openrouter_fast"))
    if not groq_key and not gemini_key and not or_key:
        print("\nERROR: Set at least one API key in backend/.env")
        return 1
    if not (selected.get("groq") or selected.get("openrouter") or selected.get("gemini")):
        print("\nWARNING: No model passed probe — check keys and rate limits.")
        return 1
    print("\nRestart uvicorn to load new models.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

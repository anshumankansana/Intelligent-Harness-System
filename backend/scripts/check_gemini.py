#!/usr/bin/env python3
"""Quick Gemini free-tier check only. Run: python scripts/check_gemini.py"""

import asyncio
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")

import httpx

from harness.providers.model_candidates import GEMINI_CANDIDATES
from harness.providers.model_registry import save_registry, load_registry


async def test_model(client: httpx.AsyncClient, key: str, model: str) -> tuple[bool, str]:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    r = await client.post(
        url,
        json={
            "contents": [{"parts": [{"text": "Reply with exactly: OK"}]}],
            "generationConfig": {"maxOutputTokens": 16, "temperature": 0},
        },
        timeout=45.0,
    )
    if r.status_code != 200:
        err = r.json().get("error", {})
        return False, f"{err.get('code', r.status_code)} — {(err.get('message') or '')[:100]}"
    parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
    if not parts:
        return False, "200 but empty response (try another model)"
    return True, parts[0].get("text", "")[:40].strip()


async def main() -> int:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    print("=" * 50)
    print("Gemini API key check (free tier)")
    print("=" * 50)

    if not key:
        print("FAIL: GEMINI_API_KEY not set in backend/.env")
        return 1

    print(f"Key loaded: yes ({len(key)} chars)\n")

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
            timeout=20.0,
        )
        if r.status_code == 200:
            print(f"API key valid — can list {len(r.json().get('models', []))} models\n")
        else:
            print(f"List models failed: HTTP {r.status_code}")
            print(r.text[:200])
            return 1

        chosen = None
        for role in ("planner", "fast"):
            print(f"[{role}]")
            for model in GEMINI_CANDIDATES.get(role, GEMINI_CANDIDATES["default"]):
                ok, detail = await test_model(client, key, model)
                mark = "OK" if ok else "FAIL"
                print(f"  [{mark}] {model}")
                print(f"        {detail}")
                if ok and not chosen:
                    chosen = model
                await asyncio.sleep(0.4)
            print()

    if chosen:
        reg = load_registry()
        reg["gemini"] = chosen
        reg["gemini_planner"] = chosen
        reg["gemini_fast"] = chosen
        save_registry(reg)
        print(f"WORKING: {chosen}")
        print("Updated selected_models.json — restart uvicorn.")
        return 0

    print("No Gemini model responded. Use Groq for planner (already configured).")
    print("Common causes: daily quota (429), wrong key, or billing not enabled on AI Studio.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

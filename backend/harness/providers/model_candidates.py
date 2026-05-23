"""Free-tier model candidates in priority order (best first)."""

from typing import Dict, List

# Groq — speed, agents, fix loops, debate
GROQ_CANDIDATES: Dict[str, List[str]] = {
    "fast": [
        "llama-3.3-70b-versatile",
        "qwen/qwen3-32b",
        "openai/gpt-oss-120b",
        "groq/compound",
        "groq/compound-mini",
        "llama-3.1-8b-instant",
    ],
    "planner": [
        "openai/gpt-oss-120b",
        "llama-3.3-70b-versatile",
        "groq/compound",
        "qwen/qwen3-32b",
    ],
    "default": [
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-120b",
        "qwen/qwen3-32b",
    ],
}

# OpenRouter — fallback; prefer :free suffix
OPENROUTER_CANDIDATES: Dict[str, List[str]] = {
    "fast": [
        "openrouter/free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-coder:free",
        "google/gemma-3-27b-it:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
    ],
    "planner": [
        "openrouter/free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-coder:free",
        "google/gemma-3-27b-it:free",
    ],
    "default": [
        "openrouter/free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-coder:free",
    ],
}

# Gemini free tier — prefer 2.5 (2.0 often hits separate quota limits)
GEMINI_CANDIDATES: Dict[str, List[str]] = {
    "planner": [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
    ],
    "fast": [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.0-flash-lite",
    ],
    "default": [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ],
}

ALL_CANDIDATES = {
    "groq": GROQ_CANDIDATES,
    "openrouter": OPENROUTER_CANDIDATES,
    "gemini": GEMINI_CANDIDATES,
}

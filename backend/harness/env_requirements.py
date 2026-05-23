"""Detect environment variables required by a generated or imported project."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ENV_LINE = re.compile(
    r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*)$", re.MULTILINE
)
ENV_REF = re.compile(
    r"(?:process\.env\.|import\.meta\.env\.)([A-Z][A-Z0-9_]+)"
    r"|process\.env\[['\"]([A-Z][A-Z0-9_]+)['\"]\]"
)

SKIP_KEYS = frozenset(
    {
        "NODE_ENV",
        "VERCEL",
        "VERCEL_ENV",
        "VERCEL_URL",
        "VERCEL_REGION",
        "CI",
        "NEXT_RUNTIME",
        "PORT",
        "HOSTNAME",
    }
)

DEMO_ENV_VALUES: dict[str, str] = {
    "OPENAI_API_KEY": "sk-demo-openai-replace-me",
    "ANTHROPIC_API_KEY": "sk-demo-anthropic-replace-me",
    "GROQ_API_KEY": "gsk_demo_replace_me",
    "GEMINI_API_KEY": "demo-gemini-replace-me",
    "OPENROUTER_API_KEY": "sk-or-demo-replace-me",
    "NEXT_PUBLIC_API_URL": "https://api.example.com",
    "NEXT_PUBLIC_APP_URL": "https://example.vercel.app",
    "DATABASE_URL": "postgresql://demo:demo@localhost:5432/demo",
    "STRIPE_SECRET_KEY": "sk_test_demo_replace_me",
    "STRIPE_PUBLISHABLE_KEY": "pk_test_demo_replace_me",
}


def _parse_env_example(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = ENV_LINE.match(line)
        if m:
            key = m.group(1)
            if key not in SKIP_KEYS:
                out[key] = m.group(2).strip().strip('"').strip("'")
    return out


def _scan_source_refs(project_dir: Path) -> set[str]:
    keys: set[str] = set()
    for pattern in ("**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx", "**/*.mjs"):
        for path in project_dir.glob(pattern):
            if "node_modules" in path.parts or ".next" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for m in ENV_REF.finditer(text):
                key = m.group(1) or m.group(2)
                if key and key not in SKIP_KEYS:
                    keys.add(key)
    return keys


def scan_project_env_requirements(run_dir: Path) -> list[dict[str, Any]]:
    """Return required env vars for workspace run (generated app or import)."""
    generated = run_dir / "generated"
    import_dir = run_dir / "import"
    project_dir = generated if generated.is_dir() and any(generated.iterdir()) else import_dir
    if not project_dir.is_dir():
        return []

    keys: dict[str, dict[str, Any]] = {}

    for name in (".env.example", ".env.local.example", "env.example"):
        example = project_dir / name
        if example.is_file():
            for key, hint in _parse_env_example(example.read_text(encoding="utf-8")).items():
                keys[key] = {
                    "key": key,
                    "required": True,
                    "description": f"From {name}",
                    "demo_value": DEMO_ENV_VALUES.get(key, ""),
                }

    for key in _scan_source_refs(project_dir):
        if key not in keys:
            keys[key] = {
                "key": key,
                "required": True,
                "description": "Referenced in application source",
                "demo_value": DEMO_ENV_VALUES.get(key, f"demo-{key.lower().replace('_', '-') }"),
            }

    spec = run_dir / "memory" / "PROJECT_SPEC.md"
    if spec.is_file():
        text = spec.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"\b([A-Z][A-Z0-9_]{2,})\b", text):
            key = m.group(1)
            if key.endswith("_KEY") or key.endswith("_URL") or key.startswith("NEXT_PUBLIC_"):
                if key not in SKIP_KEYS and key not in keys:
                    keys[key] = {
                        "key": key,
                        "required": False,
                        "description": "Mentioned in PROJECT_SPEC.md",
                        "demo_value": DEMO_ENV_VALUES.get(key, ""),
                    }

    return sorted(keys.values(), key=lambda x: x["key"])

#!/usr/bin/env python3
"""GitHub-only publish (no Vercel). Usage: python scripts/publish_github.py <run_id>"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from config import get_settings  # noqa: E402
from harness.deployment.github_publish_service import publish_run_to_github_sync  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    args = parser.parse_args()
    settings = get_settings()
    workspace = (BACKEND / settings.workspace_root).resolve()
    if not workspace.exists():
        workspace = (ROOT / "workspace").resolve()
    if not settings.github_token:
        print("GITHUB_TOKEN missing", file=sys.stderr)
        return 1
    result = publish_run_to_github_sync(args.run_id, workspace, settings.github_token)
    if result.get("ok"):
        print(f"OK: {result['github_url']}")
        return 0
    print(f"Failed: {result.get('error')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

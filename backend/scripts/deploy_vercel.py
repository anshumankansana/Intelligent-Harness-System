#!/usr/bin/env python3
"""
Deploy a harness run to Vercel (same path as the UI Deploy button).

Usage (from backend/ with venv active):
  python scripts/deploy_vercel.py <run_id>
  python scripts/deploy_vercel.py 61d9194d
  python scripts/deploy_vercel.py --list
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from config import get_settings  # noqa: E402
from harness.deployment.deploy_service import deploy_run_sync  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy harness run to Vercel")
    parser.add_argument("run_id", nargs="?", help="Run id (folder name under workspace/)")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List runs that have a generated/ folder",
    )
    args = parser.parse_args()

    settings = get_settings()
    workspace = (BACKEND / settings.workspace_root).resolve()
    if not workspace.exists():
        workspace = (ROOT / "workspace").resolve()

    if args.list or not args.run_id:
        print(f"Workspace: {workspace}\n")
        found = False
        for run_dir in sorted(workspace.iterdir()):
            if not run_dir.is_dir():
                continue
            gen = run_dir / "generated"
            if gen.is_dir() and any(gen.iterdir()):
                found = True
                print(f"  {run_dir.name}  ->  {gen}")
        if not found:
            print("No runs with generated/ found.")
        if not args.run_id:
            return 0 if args.list else 1

    if not settings.vercel_token:
        print("VERCEL_TOKEN missing in backend/.env", file=sys.stderr)
        return 1

    run_id = args.run_id.strip()
    result = deploy_run_sync(
        run_id, workspace, settings.vercel_token, settings.vercel_scope
    )
    if result.get("ok"):
        print(f"\nSuccess: {result['deploy_url']}")
        return 0
    print(f"\nFailed: {result.get('error', 'unknown')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

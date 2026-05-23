import json
from pathlib import Path
from typing import Any, Dict, Optional


def state_path(run_dir: Path) -> Path:
    return run_dir / "run_state.json"


def save_state(run_dir: Path, data: Dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path(run_dir).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_state(run_dir: Path) -> Optional[Dict[str, Any]]:
    p = state_path(run_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

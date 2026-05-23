"""Run status reconciliation tests."""
from pathlib import Path

from harness.run_state import load_state, save_state
from harness.run_status import get_run_status, is_stub_deploy_url, reconcile_run_state


def test_stub_url_detection():
    assert is_stub_deploy_url("abc123", "https://harness-demo-abc123.vercel.app")
    assert not is_stub_deploy_url("abc123", "https://my-app.vercel.app")


def test_reconcile_deploying_with_url(tmp_path: Path):
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    (run_dir / "memory").mkdir()
    (run_dir / "generated").mkdir()
    save_state(
        run_dir,
        {
            "run_id": "run1",
            "stage": "deploying",
            "deploy_url": "https://my-calc.vercel.app",
        },
    )
    state = reconcile_run_state(run_dir, persist=True)
    assert state["stage"] == "complete"
    status = get_run_status(run_dir)
    assert status["stage"] == "complete"
    assert status["progress"] == 100


def test_awaiting_approval_not_overridden_by_stale_approved(tmp_path: Path):
    run_dir = tmp_path / "run3"
    run_dir.mkdir()
    save_state(
        run_dir,
        {
            "stage": "awaiting_approval",
            "approval_status": "approved",
            "deploy_url": "https://old.vercel.app",
        },
    )
    s = get_run_status(run_dir, "approved")
    assert s["stage"] == "awaiting_approval"
    assert s["progress"] == 50


def test_get_run_status_promotes_complete_when_url_set(tmp_path: Path):
    run_dir = tmp_path / "run2"
    run_dir.mkdir()
    save_state(
        run_dir,
        {
            "stage": "deploying",
            "deploy_url": "https://real-deploy.vercel.app",
        },
    )
    s = get_run_status(run_dir)
    assert s["stage"] == "complete"

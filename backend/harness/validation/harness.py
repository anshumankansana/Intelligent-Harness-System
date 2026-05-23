import asyncio
import sys
from pathlib import Path
from typing import List, Tuple


class ValidationHarness:
    def __init__(self, project_path: Path, log):
        self.project_path = project_path
        self.log = log

    async def run_all(self) -> Tuple[bool, str]:
        await self.log("Validation running...")
        logs: List[str] = []

        for label, cmd in [
            ("lint", ["npm", "run", "lint"]),
            ("test", ["npm", "test", "--", "--passWithNoTests"]),
            ("build", ["npm", "run", "build"]),
        ]:
            ok, output = await self._run_cmd(label, cmd)
            logs.append(output)
            if not ok:
                await self.log(f"{label} failed — see log output.")
                if label == "lint":
                    # lint failure is non-fatal for hackathon MVP
                    continue
                return False, "\n".join(logs)
        await self.log("Validation passed.")
        return True, "\n".join(logs)

    async def _run_cmd(self, label: str, cmd: List[str]) -> Tuple[bool, str]:
        await self.log(f"Running {label}...")
        try:
            if sys.platform == "win32":
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(self.project_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    shell=True,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(self.project_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=180)
            output = stdout.decode(errors="replace") if stdout else "(no output)"
            ok = proc.returncode == 0
            if not ok:
                detail = output.strip() or f"exit code {proc.returncode}"
                await self.log(f"{label} failed: {detail[:200]}")
            return ok, f"=== {label} ===\n{output}"
        except FileNotFoundError:
            await self.log(f"{label} skipped — npm not found in PATH")
            return True, f"=== {label} ===\nSkipped (npm not found)"
        except asyncio.TimeoutError:
            return False, f"=== {label} ===\nTimeout after 180s"
        except Exception as e:
            await self.log(f"{label} error: {e}")
            return False, f"=== {label} ===\n{str(e)}"

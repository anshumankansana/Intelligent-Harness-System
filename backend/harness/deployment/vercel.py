import asyncio
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from harness.deployment.project_repair import repair_nextjs_project
from harness.deployment.vercel_env import apply_vercel_env
from harness.deployment.vercel_scope import resolve_vercel_scope

VERCEL_CLI_PKG = "vercel@latest"


def _safe_log_text(text: str) -> str:
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


class VercelDeployer:
    def __init__(self, token: str, log, scope: str = ""):
        self.token = token
        self.log = log
        self._scope = (scope or os.environ.get("VERCEL_SCOPE", "")).strip()
        self._npm_exe: Optional[str] = None
        self._npx_exe: Optional[str] = None

    async def deploy(
        self,
        project_name: str,
        project_dir: Path,
        github_repo_url: str = "",
        project_env: dict | None = None,
    ) -> Optional[str]:
        del github_repo_url
        if not self.token:
            await self.log("VERCEL_TOKEN not set — skipping Vercel deployment.")
            return None

        project_dir = Path(project_dir)
        if not project_dir.is_dir():
            await self.log(f"Vercel: project directory missing ({project_dir})")
            return None

        if not self._resolve_npm():
            await self.log(
                "Node/npm not found. Install Node.js LTS, restart the backend, "
                "or add C:\\Program Files\\nodejs to PATH."
            )
            return None

        fixes = repair_nextjs_project(project_dir)
        if fixes:
            await self.log("Deploy prep: " + "; ".join(fixes))

        if not self._scope:
            self._scope = resolve_vercel_scope(self.token, project_dir)
        await self.log(f"Vercel team scope: {self._scope}")

        await self.log(f"Vercel: deploying '{project_name}' (install -> build -> deploy)...")

        built = await self._npm_install_build(project_dir)
        if not built:
            await self.log("Local npm build failed - Vercel will build remotely.")

        # Deploy first — `vercel deploy` can create/link the project without a separate link step
        url = await self._deploy_cli(project_dir)
        if url:
            return url

        if built:
            url = await self._deploy_prebuilt_cli(project_dir)
            if url:
                return url

        linked = await self._link_project(project_dir, project_name)
        if not linked:
            await self.log("Vercel link skipped or timed out — retrying deploy once more.")

        if project_env and linked:
            await apply_vercel_env(
                self.token, project_dir, project_env, self.log, scope=self._scope
            )

        url = await self._deploy_cli(project_dir)
        if url:
            return url

        if built:
            url = await self._deploy_prebuilt_cli(project_dir)
            if url:
                return url

        await self.log(
            "Vercel deploy failed. Set VERCEL_SCOPE in backend/.env if needed "
            "(e.g. anshumans-projects-671c73a5). Check logs above."
        )
        return None

    def _resolve_npm(self) -> bool:
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        npx = shutil.which("npx.cmd") or shutil.which("npx")
        if npm:
            self._npm_exe = npm
        if npx:
            self._npx_exe = npx
        return bool(self._npm_exe)

    def _node_env(self) -> dict[str, str]:
        env = {**os.environ}
        env["CI"] = "1"
        env["VERCEL"] = "1"
        env["FORCE_COLOR"] = "0"
        extra_paths = [
            r"C:\Program Files\nodejs",
            os.path.expanduser(r"~\AppData\Roaming\npm"),
        ]
        path = env.get("PATH", "")
        for p in extra_paths:
            if os.path.isdir(p) and p.lower() not in path.lower():
                path = p + os.pathsep + path
        env["PATH"] = path
        # Do not set VERCEL_ORG_ID here — it conflicts with CLI --scope unless PROJECT_ID is also set.
        env.pop("VERCEL_ORG_ID", None)
        env.pop("VERCEL_PROJECT_ID", None)
        return env

    def _vercel_args(self, *args: str) -> list[str]:
        npx = self._npx_exe or ("npx.cmd" if sys.platform == "win32" else "npx")
        cmd = [npx, "--yes", VERCEL_CLI_PKG, *args, f"--token={self.token}"]
        if self._scope:
            cmd.append(f"--scope={self._scope}")
        return cmd

    async def _run_cmd(
        self, project_dir: Path, args: list[str], label: str, timeout_sec: int = 600
    ) -> tuple[bool, str]:
        await self.log(f"Running {label}...")
        env = self._node_env()
        cwd = str(project_dir)

        def run_sync() -> tuple[int, str]:
            try:
                proc = subprocess.run(
                    args,
                    cwd=cwd,
                    capture_output=True,
                    env=env,
                    shell=False,
                    timeout=timeout_sec,
                )
                out = (proc.stdout or b"") + (proc.stderr or b"")
                return proc.returncode, out.decode(errors="replace")
            except subprocess.TimeoutExpired as te:
                if te.process is not None:
                    with contextlib.suppress(Exception):
                        te.process.kill()
                return -1, f"Command timed out after {timeout_sec}s — continuing with next step"
            except Exception as e:
                return -1, str(e)

        heartbeat: asyncio.Task | None = None

        async def pulse() -> None:
            elapsed = 0
            while True:
                await asyncio.sleep(30)
                elapsed += 30
                await self.log(f"Still running {label}… ({elapsed}s elapsed)")

        try:
            heartbeat = asyncio.create_task(pulse())
            code, output = await asyncio.to_thread(run_sync)
            ok = code == 0
            if output.strip():
                tail = output[-4000:] if len(output) > 4000 else output
                await self.log(_safe_log_text(tail))
            if not ok:
                if not self._scope and "missing_scope" in output:
                    self._scope = resolve_vercel_scope(
                        self.token, project_dir, cli_output=output
                    )
                    await self.log(f"Detected Vercel scope: {self._scope} — retrying {label}...")
                    return await self._run_cmd(project_dir, self._refresh_scope_args(args), label)
                hint = output.strip() or f"exit code {code}"
                await self.log(_safe_log_text(f"{label} failed: {hint[:800]}"))
            return ok, output
        except Exception as e:
            await self.log(f"{label} failed: {e!r}")
            return False, str(e)
        finally:
            if heartbeat:
                heartbeat.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat

    def _refresh_scope_args(self, args: list[str]) -> list[str]:
        """Re-build vercel CLI args with newly resolved scope."""
        if not args or "vercel" not in " ".join(args).lower():
            return args
        cleaned = []
        for a in args:
            if a.startswith("--scope="):
                continue
            cleaned.append(a)
        if self._scope:
            cleaned.append(f"--scope={self._scope}")
        return cleaned

    async def _link_project(self, project_dir: Path, project_name: str) -> bool:
        vercel_dir = project_dir / ".vercel" / "project.json"
        if vercel_dir.is_file():
            await self.log("Vercel project already linked — skipping vercel link.")
            return True
        ok, out = await self._run_cmd(
            project_dir,
            self._vercel_args("link", "--yes", f"--project={project_name}"),
            "vercel link",
            timeout_sec=120,
        )
        if ok:
            return True
        if "missing_scope" in out and not self._scope:
            self._scope = resolve_vercel_scope(self.token, project_dir, cli_output=out)
        return False

    async def _npm_install_build(self, project_dir: Path) -> bool:
        if not (project_dir / "package.json").exists() or not self._npm_exe:
            return True
        ok, _ = await self._run_cmd(
            project_dir,
            [self._npm_exe, "install", "--legacy-peer-deps"],
            "npm install",
        )
        if not ok:
            return False
        ok, _ = await self._run_cmd(
            project_dir, [self._npm_exe, "run", "build"], "npm run build"
        )
        return ok

    async def _deploy_prebuilt_cli(self, project_dir: Path) -> Optional[str]:
        ok, out = await self._run_cmd(
            project_dir, self._vercel_args("build"), "vercel build"
        )
        if not ok:
            return None
        ok, out2 = await self._run_cmd(
            project_dir,
            self._vercel_args("deploy", "--prebuilt", "--prod", "--yes"),
            "vercel deploy --prebuilt",
            timeout_sec=900,
        )
        if not ok:
            return None
        url = self._parse_deploy_url(out2 or out)
        if url:
            await self.log(f"Vercel deploy complete: {url}")
        return url

    async def _deploy_cli(self, project_dir: Path) -> Optional[str]:
        ok, output = await self._run_cmd(
            project_dir,
            self._vercel_args("deploy", "--prod", "--yes"),
            "vercel deploy",
            timeout_sec=900,
        )
        if not ok:
            return None
        url = self._parse_deploy_url(output)
        if url:
            await self.log(f"Vercel deploy complete: {url}")
        return url

    def _parse_deploy_url(self, output: str) -> Optional[str]:
        patterns = [
            r"Aliased\s+(https://[^\s]+)",
            r"Production:\s*(https://[^\s]+)",
            r'"url":\s*"(https://[^"]+vercel\.app[^"]*)"',
            r"https://[a-z0-9][a-z0-9.-]+\.vercel\.app",
        ]
        seen: set[str] = set()
        for pat in patterns:
            for m in re.findall(pat, output, re.IGNORECASE):
                url = (m if isinstance(m, str) else m[0]).rstrip(").,;'\"")
                if "vercel.app" not in url.lower() or url in seen:
                    continue
                seen.add(url)
                if pat.startswith("Aliased"):
                    return url
        for url in seen:
            if re.match(r"https://[a-z0-9-]+\.vercel\.app$", url, re.I):
                return url
        return next(iter(seen), None)

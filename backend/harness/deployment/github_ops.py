import subprocess
from pathlib import Path
from typing import Optional

GITIGNORE_LINES = """
node_modules/
.next/
.vercel/
.env
.env.local
*.log
.DS_Store
""".strip()


class GitHubAutomation:
    """Push generated project to GitHub — git only, never deploy."""

    def __init__(self, token: str, log):
        self.token = token
        self.log = log

    def _ensure_gitignore(self, project_path: Path) -> None:
        gi = project_path / ".gitignore"
        existing = gi.read_text(encoding="utf-8", errors="replace") if gi.exists() else ""
        needed = [line for line in GITIGNORE_LINES.splitlines() if line and line not in existing]
        if needed:
            block = (existing.rstrip() + "\n" + "\n".join(needed) + "\n") if existing else (
                GITIGNORE_LINES + "\n"
            )
            gi.write_text(block, encoding="utf-8")

    def _run_git(self, project_path: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=check,
        )

    async def push_project(self, project_path: Path, repo_name: str) -> Optional[str]:
        if not self.token:
            await self.log("GITHUB_TOKEN not set — skipping GitHub push.")
            return None

        project_path = Path(project_path)
        await self.log("GitHub: preparing repository (git push only, no deploy)...")

        try:
            from github import Github

            g = Github(self.token)
            user = g.get_user()
            repo_url_public = None

            try:
                repo = user.get_repo(repo_name)
                repo_url_public = repo.html_url
                await self.log(f"GitHub: using existing repo {repo_name}")
            except Exception:
                repo = user.create_repo(repo_name, private=False, auto_init=False)
                repo_url_public = repo.html_url
                await self.log(f"GitHub: created repo {repo_name}")

            auth_url = repo.clone_url.replace("https://", f"https://{self.token}@")

            self._ensure_gitignore(project_path)

            git_dir = project_path / ".git"
            if not git_dir.exists():
                self._run_git(project_path, ["init"])
                self._run_git(project_path, ["branch", "-M", "main"])

            # Set or update origin
            remote = self._run_git(project_path, ["remote"], check=False)
            if "origin" in (remote.stdout or ""):
                self._run_git(project_path, ["remote", "set-url", "origin", auth_url], check=False)
            else:
                self._run_git(project_path, ["remote", "add", "origin", auth_url], check=False)

            self._run_git(project_path, ["add", "-A"])
            status = self._run_git(project_path, ["status", "--porcelain"], check=False)
            if not (status.stdout or "").strip():
                await self.log("GitHub: no file changes to commit.")
            else:
                self._run_git(
                    project_path,
                    ["commit", "-m", "Update from Intelligent Harness"],
                    check=False,
                )

            push = self._run_git(
                project_path, ["push", "-u", "origin", "main"], check=False
            )
            if push.returncode != 0:
                # First push to empty repo may need -f only if histories diverge; try plain push first
                err = (push.stderr or push.stdout or "push failed")[:800]
                await self.log(f"GitHub push error: {err}")
                return None

            await self.log(f"GitHub push complete: {repo_url_public}")
            return repo_url_public
        except Exception as e:
            await self.log(f"GitHub automation failed: {e}")
            return None

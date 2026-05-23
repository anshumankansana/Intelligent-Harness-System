import base64
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote

COMMIT_MESSAGE = "Initial commit from Intelligent Harness"
UPDATE_COMMIT_MESSAGE = "Update from Intelligent Harness"

GITIGNORE_LINES = """
node_modules/
.next/
.vercel/
.env
.env.local
*.log
.DS_Store
""".strip()

SKIP_DIR_NAMES = {".git", "node_modules", ".next", ".vercel"}


class GitHubAutomation:
    """Push generated project to GitHub — git only, never deploy."""

    def __init__(self, token: str, log):
        self.token = token
        self.log = log

    def _auth_clone_url(self, clone_url: str) -> str:
        """Embed token safely (special characters in PATs break naive string replace)."""
        if not clone_url.startswith("https://"):
            return clone_url
        rest = clone_url[len("https://") :]
        return f"https://{quote(self.token, safe='')}@{rest}"

    def _ensure_gitignore(self, project_path: Path) -> None:
        gi = project_path / ".gitignore"
        existing = gi.read_text(encoding="utf-8", errors="replace") if gi.exists() else ""
        needed = [line for line in GITIGNORE_LINES.splitlines() if line and line not in existing]
        if needed:
            block = (
                (existing.rstrip() + "\n" + "\n".join(needed) + "\n")
                if existing
                else (GITIGNORE_LINES + "\n")
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

    def _ensure_git_identity(self, project_path: Path) -> None:
        self._run_git(project_path, ["config", "user.email", "harness@ihs.local"], check=False)
        self._run_git(project_path, ["config", "user.name", "Intelligent Harness"], check=False)

    def _list_trackable_files(self, project_path: Path) -> list[Path]:
        files: list[Path] = []
        for p in project_path.rglob("*"):
            if not p.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in p.parts):
                continue
            files.append(p)
        return files

    def _prepare_local_commit(self, project_path: Path) -> Tuple[bool, str, int]:
        """Fresh git repo with at least one commit. Returns (ok, error, file_count)."""
        git_dir = project_path / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)

        trackable = self._list_trackable_files(project_path)
        if not trackable:
            return False, "Generated project folder has no files to publish.", 0

        self._ensure_gitignore(project_path)
        self._run_git(project_path, ["init"])
        self._ensure_git_identity(project_path)

        self._run_git(project_path, ["add", "-A"], check=False)
        force = self._run_git(project_path, ["add", "-f", "package.json", "README.md"], check=False)
        if force.returncode != 0:
            for name in ("index.html", "app", "src", "pages", "public"):
                p = project_path / name
                if p.exists():
                    self._run_git(project_path, ["add", "-f", name], check=False)

        status = self._run_git(project_path, ["status", "--porcelain"], check=False)
        if not (status.stdout or "").strip():
            return (
                False,
                "Git could not stage any project files (check .gitignore on the server).",
                len(trackable),
            )

        commit = self._run_git(
            project_path,
            ["commit", "-m", COMMIT_MESSAGE],
            check=False,
        )
        if commit.returncode != 0:
            err = (commit.stderr or commit.stdout or "git commit failed")[:800]
            return False, f"Git commit failed: {err}", len(trackable)

        self._run_git(project_path, ["branch", "-M", "main"], check=False)

        listed = self._run_git(project_path, ["ls-files"], check=False)
        n = len([ln for ln in (listed.stdout or "").splitlines() if ln.strip()])
        if n == 0:
            return False, "Commit succeeded but no files in git index.", 0
        return True, "", n

    async def _push_via_contents_api(
        self,
        user,
        repo_name: str,
        project_path: Path,
        repo_url_public: str,
    ) -> Tuple[Optional[str], str]:
        """Fallback when git push fails — upload files via GitHub Contents API."""
        from github import Github

        try:
            repo = user.get_repo(repo_name)
        except Exception:
            return None, "Repository not found for API upload."

        trackable = self._list_trackable_files(project_path)
        if not trackable:
            return None, "No files to upload."

        await self.log(f"GitHub: uploading {len(trackable)} file(s) via API fallback…")
        uploaded = 0
        branch = "main"

        for fp in sorted(trackable, key=lambda p: str(p).lower()):
            rel = fp.relative_to(project_path).as_posix()
            try:
                raw = fp.read_bytes()
            except OSError as e:
                await self.log(f"GitHub: skip {rel} ({e})")
                continue

            try:
                text = raw.decode("utf-8")
                payload = text
            except UnicodeDecodeError:
                payload = base64.b64encode(raw).decode("ascii")

            try:
                existing = repo.get_contents(rel, ref=branch)
                repo.update_file(
                    rel,
                    UPDATE_COMMIT_MESSAGE,
                    payload,
                    existing.sha,
                    branch=branch,
                )
            except Exception:
                try:
                    repo.create_file(
                        rel,
                        COMMIT_MESSAGE if uploaded == 0 else UPDATE_COMMIT_MESSAGE,
                        payload,
                        branch=branch,
                    )
                except Exception as e:
                    await self.log(f"GitHub API upload failed for {rel}: {e}")
                    continue
            uploaded += 1

        if uploaded == 0:
            return None, "GitHub API upload failed for all files."
        await self.log(f"GitHub: API upload complete ({uploaded} files).")
        return repo_url_public, ""

    async def push_project(self, project_path: Path, repo_name: str) -> Tuple[Optional[str], str]:
        if not self.token:
            msg = "GITHUB_TOKEN not set on the API server (Render .env or Environment page)."
            await self.log(msg)
            return None, msg

        if not shutil.which("git"):
            msg = "git is not installed on the API server — GitHub publish unavailable."
            await self.log(msg)
            return None, msg

        project_path = Path(project_path).resolve()
        await self.log("GitHub: preparing repository (git push only, no deploy)...")

        ok, prep_err, file_count = self._prepare_local_commit(project_path)
        if not ok:
            await self.log(f"[ERR] {prep_err}")
            return None, prep_err

        await self.log(f"GitHub: local commit ready ({file_count} file(s) tracked).")

        try:
            from github import Github

            g = Github(self.token)
            user = g.get_user()

            try:
                repo = user.get_repo(repo_name)
                repo_url_public = repo.html_url
                await self.log(f"GitHub: using existing repo {repo_name}")
            except Exception:
                repo = user.create_repo(repo_name, private=False, auto_init=False)
                repo_url_public = repo.html_url
                await self.log(f"GitHub: created repo {repo_name}")

            auth_url = self._auth_clone_url(repo.clone_url)

            remote = self._run_git(project_path, ["remote"], check=False)
            if "origin" in (remote.stdout or ""):
                self._run_git(project_path, ["remote", "set-url", "origin", auth_url], check=False)
            else:
                self._run_git(project_path, ["remote", "add", "origin", auth_url], check=False)

            push = self._run_git(
                project_path, ["push", "-u", "origin", "main"], check=False
            )
            if push.returncode != 0:
                err = (push.stderr or push.stdout or "git push failed")[:800]
                await self.log(f"GitHub push error: {err} — trying force push…")
                push = self._run_git(
                    project_path, ["push", "-u", "origin", "main", "--force"],
                    check=False,
                )

            if push.returncode == 0:
                await self.log(f"GitHub push complete: {repo_url_public}")
                return repo_url_public, ""

            err = (push.stderr or push.stdout or "git push failed")[:800]
            await self.log(f"GitHub push failed: {err} — trying Contents API…")
            hint = ""
            if "403" in err or "Permission" in err:
                hint = " Token needs repo scope (classic: repo; fine-grained: Contents read/write)."

            api_url, api_err = await self._push_via_contents_api(
                user, repo_name, project_path, repo_url_public
            )
            if api_url:
                return api_url, ""
            return None, f"Git push failed: {err}{hint}. API fallback: {api_err}"
        except Exception as e:
            await self.log(f"GitHub automation failed: {e}")
            return None, str(e)[:800]

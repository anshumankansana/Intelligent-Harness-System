import io
import shutil
import zipfile
from pathlib import Path
from typing import List


def safe_extract_zip(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            target = (dest / member).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise ValueError(f"Unsafe zip path: {member}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(target, "wb") as out:
                out.write(src.read())


def flatten_single_root_folder(dest: Path) -> None:
    """If zip had one top-level folder, hoist contents up into dest."""
    children = [p for p in dest.iterdir() if p.name not in (".git",)]
    if len(children) == 1 and children[0].is_dir():
        root = children[0]
        for item in list(root.iterdir()):
            shutil.move(str(item), str(dest / item.name))
        try:
            root.rmdir()
        except OSError:
            pass


def list_project_tree(root: Path, max_files: int = 80) -> str:
    lines: List[str] = []
    count = 0
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            rel = path.relative_to(root)
            lines.append(str(rel).replace("\\", "/"))
            count += 1
            if count >= max_files:
                lines.append("... (truncated)")
                break
    return "\n".join(lines) if lines else "(empty)"


def build_zip_bytes(source_dir: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                arc = path.relative_to(source_dir).as_posix()
                zf.write(path, arc)
    buf.seek(0)
    return buf.getvalue()

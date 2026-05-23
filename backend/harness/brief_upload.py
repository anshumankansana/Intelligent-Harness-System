"""Save uploaded brief documents and extract text."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from harness.document_reader import (
    allowed_document_name,
    extract_docx_text,
    persist_brief_markdown,
)


async def extract_brief_upload(upload: UploadFile) -> Tuple[str, str]:
    """Read .docx from upload without persisting (for pre-run extraction)."""
    filename = (upload.filename or "brief.docx").strip()
    if not allowed_document_name(filename):
        raise ValueError("Only .docx Word documents are supported")
    data = await upload.read()
    if not data:
        raise ValueError("Uploaded file is empty")
    if len(data) > 15 * 1024 * 1024:
        raise ValueError("Document must be under 15 MB")
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        text = extract_docx_text(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return text, filename


async def save_and_extract_brief(
    upload: UploadFile,
    run_dir: Path,
    subdir: str = "uploads",
) -> Tuple[str, str, Path]:
    """
    Save .docx to workspace, extract text.
    Returns (text, filename, saved_path).
    """
    filename = (upload.filename or "brief.docx").strip()
    if not allowed_document_name(filename):
        raise ValueError("Only .docx Word documents are supported")

    dest_dir = run_dir / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}-{Path(filename).name}"
    dest_path = dest_dir / safe_name

    data = await upload.read()
    if not data:
        raise ValueError("Uploaded file is empty")
    if len(data) > 15 * 1024 * 1024:
        raise ValueError("Document must be under 15 MB")

    dest_path.write_bytes(data)
    text = extract_docx_text(dest_path)
    return text, filename, dest_path

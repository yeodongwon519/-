from __future__ import annotations

import hashlib
from pathlib import Path


def file_sha256(path: Path, *, prefix_only: int = 16) -> str:
    """Hash a file in 1 MB chunks. Returns hex prefix (default 16 chars = 64 bits)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    digest = h.hexdigest()
    return digest[:prefix_only] if prefix_only else digest


def cache_dir_for(video: Path, root: Path = Path("cache")) -> Path:
    sha = file_sha256(video)
    out = root / sha
    out.mkdir(parents=True, exist_ok=True)
    return out

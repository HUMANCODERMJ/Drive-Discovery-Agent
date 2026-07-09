"""Local filesystem search client with restricted-directory enforcement."""

import os
from datetime import datetime
from pathlib import Path

EXCLUDED_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico",
    ".tiff", ".tif", ".heic", ".heif", ".raw",
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v",
}


def _is_restricted(path: Path, restricted_dirs: list[Path]) -> bool:
    """Return True if path is inside any restricted directory."""
    for r in restricted_dirs:
        try:
            path.relative_to(r)
            return True
        except ValueError:
            continue
    return False


def _parse_restricted(raw: str) -> list[Path]:
    """Parse semicolon-separated restricted dir string from config."""
    if not raw or not raw.strip():
        return []
    return [Path(p.strip()).resolve() for p in raw.split(";") if p.strip()]


def _mime_from_ext(ext: str) -> str:
    """Return a rough MIME type label from file extension."""
    ext = ext.lower()
    mime_map = {
        ".pdf":  "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc":  "application/msword",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls":  "application/vnd.ms-excel",
        ".csv":  "text/csv",
        ".txt":  "text/plain",
        ".md":   "text/markdown",
        ".py":   "text/x-python",
        ".js":   "text/javascript",
        ".ts":   "text/typescript",
        ".json": "application/json",
        ".html": "text/html",
        ".xml":  "application/xml",
    }
    return mime_map.get(ext, f"application/{ext.lstrip('.') or 'octet-stream'}")


def search_local_files(
    root_dir: str,
    restricted_raw: str = "",
    name_contains: str = "",
    extensions: list[str] | None = None,
    modified_after: str = "",
    modified_before: str = "",
    max_results: int = 20,
) -> list[dict]:
    """
    Recursively walk root_dir and return files matching all supplied filters.

    Args:
        root_dir:        User-supplied root path to search.
        restricted_raw:  Semicolon-separated restricted dirs from config.
        name_contains:   Substring match against filename (case-insensitive).
        extensions:      List of extensions to include e.g. ['.pdf', '.docx'].
        modified_after:  ISO date string 'YYYY-MM-DD'; exclude files older than this.
        modified_before: ISO date string 'YYYY-MM-DD'; exclude files newer than this.
        max_results:     Cap on returned results.

    Returns:
        List of file dicts with keys: name, path, mimeType, modifiedTime, size.

    Raises:
        ValueError: If root_dir is restricted, invalid, or does not exist.
        RuntimeError: If os.walk fails unexpectedly.
    """
    root = Path(root_dir).resolve()
    restricted_dirs = _parse_restricted(restricted_raw)

    if not root.exists():
        raise ValueError(f"Directory does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"Path is not a directory: {root}")
    if _is_restricted(root, restricted_dirs):
        raise ValueError(f"Access to '{root}' is restricted by policy.")

    dt_after = datetime.fromisoformat(modified_after) if modified_after else None
    dt_before = datetime.fromisoformat(modified_before) if modified_before else None

    exts_lower: set[str] | None = (
        {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions}
        if extensions
        else None
    )

    results: list[dict] = []

    try:
        for dirpath, dirnames, filenames in os.walk(root):
            current_dir = Path(dirpath).resolve()

            # Prune restricted subdirs in-place so os.walk skips them
            dirnames[:] = [
                d for d in dirnames
                if not _is_restricted(current_dir / d, restricted_dirs)
            ]

            for filename in filenames:
                if len(results) >= max_results:
                    break

                file_path = current_dir / filename
                ext = file_path.suffix.lower()

                # Skip excluded types (images, videos)
                if ext in EXCLUDED_EXTENSIONS:
                    continue

                # Extension filter
                if exts_lower and ext not in exts_lower:
                    continue

                # Name filter
                if name_contains and name_contains.lower() not in filename.lower():
                    continue

                # Date filters
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    size = file_path.stat().st_size
                except OSError:
                    continue

                if dt_after and mtime < dt_after:
                    continue
                if dt_before and mtime > dt_before:
                    continue

                results.append({
                    "name":         filename,
                    "path":         str(file_path),
                    "mimeType":     _mime_from_ext(ext),
                    "modifiedTime": mtime.isoformat(),
                    "size":         size,
                })

            if len(results) >= max_results:
                break

    except PermissionError as exc:
        raise RuntimeError(f"Permission denied during filesystem walk: {exc}") from exc

    return results
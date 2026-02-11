"""Project path discovery utilities.

The codebase currently stores runtime configuration in a repo-root `.env`.
Relying on CWD for `.env` resolution is a common source of confusion, so we
attempt to locate the project root by walking up from a start directory.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


def find_project_root(start: Path) -> Path | None:
    """Find the nearest parent directory containing `pyproject.toml`.

    Args:
        start: Directory to start searching from.

    Returns:
        The project root path, or None if not found.
    """
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return None


def require_project_root(start: Path | None = None) -> Path:
    """Like find_project_root but raises a user-friendly error if missing."""
    start = (start or Path.cwd()).resolve()
    root = find_project_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate project root (pyproject.toml not found). "
            "Run this command from the repository root."
        )
    return root


@lru_cache(maxsize=1)
def project_root_cached() -> Path | None:
    """Cached best-effort project root for runtime config loading."""
    return find_project_root(Path.cwd())


def default_env_file() -> Path:
    """Return the default `.env` path (repo root if discovered, else CWD)."""
    root = project_root_cached() or Path.cwd().resolve()
    return root / ".env"


def default_env_example_file() -> Path:
    """Return the default `.env.example` path (repo root if discovered, else CWD)."""
    root = project_root_cached() or Path.cwd().resolve()
    return root / ".env.example"


import pathlib
import sys


def _ensure_repo_root_on_path() -> None:
    """Add repository root to sys.path so `backend` can be imported as a top-level package."""
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


_ensure_repo_root_on_path()


"""Force-rebuild every species' 52 weekly grids.

    python scripts/rebuild_cache.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flyway.simulate import ensure_all  # noqa: E402

if __name__ == "__main__":
    ensure_all(force=True, verbose=True)
    print("Done.")

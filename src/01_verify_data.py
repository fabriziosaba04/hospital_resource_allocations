"""Step 1 of the pipeline: verify the frozen datasets (tag data-v1.0) against data/MANIFEST.json.

    uv run python src/01_verify_data.py                 # hashes, completeness, generator code
    uv run python src/01_verify_data.py --regenerate    # also rebuild all four datasets from their seeds, byte for byte

Thin wrapper around `python -m src.data_generation.manifest --verify`. The datasets were generated once by
`python -m src.data_generation --seed <s>` (PROJECT_SPEC.md §7) and are never regenerated in place.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_generation.manifest import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["--verify", "--root", str(ROOT), *sys.argv[1:]]))

"""Generate and validate one dataset (PROJECT_SPEC.md §7).

    uv run python -m src.data_generation --seed 20261107
    uv run python -m src.data_generation --config <generation_config> --env <environment_config> --seed <s>

Exit code 0 if every check passes; 1 if the dataset is rejected (the report records why).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .generator import generate, load_json, write_dataset
from .stats import compute_stats, typed
from .validation import load_dataset, validate_dataset

CONFIG_DIR = Path(__file__).parent / "configs"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=str(CONFIG_DIR / "generation_config.json"))
    p.add_argument("--env", default=str(CONFIG_DIR / "environment_config.json"))
    p.add_argument("--seed", type=int, default=None, help="overrides the seed in the generation config")
    p.add_argument("--dataset-id", default=None,
                   help="override the dataset_id (default seed<seed>); for labelled variants such as a stress case")
    p.add_argument("--root", default=".", help="project root under which data/ is written")
    p.add_argument("--overwrite", action="store_true", help="replace an existing dataset (raw data is otherwise immutable)")
    p.add_argument("--stats", action="store_true", help="print descriptive statistics after validation")
    args = p.parse_args(argv)

    gen_cfg, env_cfg = load_json(args.config), load_json(args.env)
    seed = args.seed if args.seed is not None else int(gen_cfg["seed"])
    ds = generate(gen_cfg, env_cfg, seed, dataset_id=args.dataset_id or gen_cfg.get("dataset_id"))
    write_dataset(ds, args.root, overwrite=args.overwrite)
    report = validate_dataset(args.root, ds.dataset_id)

    print(f"dataset {ds.dataset_id}: {report['n_passed']}/{report['n_checks']} checks passed -> "
          f"{'ACCEPTED' if report['accepted'] else 'REJECTED'}")
    for c in report["checks"]:
        if not c["passed"]:
            print(f"  FAIL {c['check_id']}: {c['n_failures']} failure(s), e.g. {c['examples']}")
    if args.stats:
        data = typed(load_dataset(args.root, ds.dataset_id))
        st = compute_stats(data["resources"], data["demand"], data["registry"], data["environment_config"])
        print(json.dumps(st, indent=2))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())

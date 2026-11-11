"""Monte Carlo reference ranges for the generator (seeds 1..n, disjoint from the dataset seeds).

    uv run python -m src.data_generation.montecarlo --n 1000 [--compare seed20261107]

The summary is written to data/processed/montecarlo/montecarlo_summary.json. It describes the
generation process and must stay hidden from agents in run sessions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .generator import generate, load_json
from .stats import compute_stats, scalar_metrics, typed
from .validation import load_dataset

CONFIG_DIR = Path(__file__).parent / "configs"


def run(n: int, gen_cfg: dict, env_cfg: dict) -> dict[str, np.ndarray]:
    rows: dict[str, list[float]] = {}
    for seed in range(1, n + 1):
        ds = generate(gen_cfg, env_cfg, seed)
        for k, v in scalar_metrics(compute_stats(ds.resources, ds.demand, ds.registry, env_cfg)).items():
            rows.setdefault(k, []).append(float(v))
    return {k: np.array(v) for k, v in rows.items()}


def summarise(samples: dict[str, np.ndarray], compare: dict[str, float] | None = None) -> dict:
    out = {}
    for k, a in samples.items():
        s = {
            "mean": float(a.mean()), "sd": float(a.std(ddof=1)),
            "p2.5": float(np.percentile(a, 2.5)), "p50": float(np.percentile(a, 50)),
            "p97.5": float(np.percentile(a, 97.5)), "min": float(a.min()), "max": float(a.max()),
        }
        if compare is not None:
            v = float(compare[k])
            # mid-rank percentile: share of MC draws below v, plus half the ties
            s["dataset_value"] = v
            s["dataset_percentile"] = float(100 * ((a < v).mean() + 0.5 * (a == v).mean()))
            s["dataset_within_95"] = bool(s["p2.5"] <= v <= s["p97.5"])
        out[k] = s
    return out


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--config", default=str(CONFIG_DIR / "generation_config.json"))
    p.add_argument("--env", default=str(CONFIG_DIR / "environment_config.json"))
    p.add_argument("--compare", default=None, help="dataset_id to place within the Monte Carlo ranges")
    p.add_argument("--root", default=".")
    args = p.parse_args(argv)

    gen_cfg, env_cfg = load_json(args.config), load_json(args.env)
    samples = run(args.n, gen_cfg, env_cfg)
    compare = None
    if args.compare:
        data = typed(load_dataset(args.root, args.compare))
        compare = scalar_metrics(compute_stats(data["resources"], data["demand"], data["registry"], data["environment_config"]))
    summary = {"n_seeds": args.n, "seeds": f"1..{args.n}", "compared_dataset": args.compare,
               "metrics": summarise(samples, compare)}
    out = Path(args.root) / "data" / "processed" / "montecarlo"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "montecarlo_summary.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

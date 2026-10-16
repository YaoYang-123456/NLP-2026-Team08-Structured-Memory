"""Explicit user-started bounded stability session; no scheduler or automatic resume."""
import argparse
import time
from pathlib import Path
import evening_smoke


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--started-epoch", type=float, help="Original work-start time; default now")
    args = p.parse_args()
    started = args.started_epoch if args.started_epoch is not None else time.time()
    remaining = started + 120 * 60 - time.time()
    if remaining <= 600:
        p.error("Less than ten minutes remain; do not start inference")
    evening_smoke.ACTIVE_SECONDS = remaining - 600
    evening_smoke.TOTAL_SECONDS = remaining
    raise SystemExit(evening_smoke.start(args.out.resolve(),
                     evening_smoke.ROOT / "configs/qwen-stability-sampling.json",
                     evening_smoke.ROOT / "scripts/run_stability.py"))

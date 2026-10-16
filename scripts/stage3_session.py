"""Explicit stage-three start/resume; original frozen clock and global request cap persist."""
import argparse
import os
import time
from pathlib import Path
import evening_smoke
from metamem_pilot.data import read, write_atomic

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--resume-from", type=Path, help="Previous smoke directory; only not-started slots continue")
    args = p.parse_args()
    plan = read(evening_smoke.ROOT / "configs/metamem-stage3-plan.json")
    remaining = plan["total_deadline_epoch"] - time.time()
    if remaining <= 600:
        p.error("Original task budget expired or cleanup window reached")
    evening_smoke.ACTIVE_SECONDS = min(plan["inference_deadline_epoch"]-time.time(), remaining-600)
    evening_smoke.TOTAL_SECONDS = remaining
    registry = evening_smoke.ROOT / "output/stage3-session-registry.json"
    if registry.exists():
        previous = read(registry)
        if not args.resume_from or args.resume_from.resolve() != Path(previous["latest_session"]) / "smoke":
            p.error("A session already exists; resume only its latest smoke directory, never reset the request budget")
    elif args.resume_from:
        p.error("Resume registry missing; inspect saved provenance before restarting")
    if args.out.exists():
        p.error("Output already exists")
    write_atomic(registry, {"latest_session":str(args.out.resolve()), "goal_start_epoch":plan["goal_start_epoch"]})
    if args.resume_from:
        os.environ["METAMEM_STAGE3_RESUME_FROM"] = str(args.resume_from.resolve())
    else:
        os.environ.pop("METAMEM_STAGE3_RESUME_FROM", None)
    raise SystemExit(evening_smoke.start(args.out.resolve(), evening_smoke.ROOT / plan["generation_config"], evening_smoke.ROOT / "scripts/run_stage3.py"))

"""Command line: python -m pipeline <command>.

  film       validate -> narration -> timeline -> keyframes -> music -> shots -> assemble/QC -> costs
  radio      narration + score over black (the Phase 1 prototype)
  validate   schema + cross-checks only
  narration | keyframes | music | shots | assemble   one stage (earlier outputs must exist)
  smoke      one cheap call per provider, logged
  costs      rewrite the measured table in COSTS.md from runs.jsonl

Every stage is cached by a hash of its inputs, so `film` after a one-line storyboard edit
regenerates only what that edit touched. The summary at the end counts this run's model calls.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from . import assemble, keyframes, music, narration, shots, timeline
from .common import OUTPUTS, ROOT, RUN_ID, RUNS_LOG, PermanentError, load_storyboard


def _speech(board: dict) -> dict[str, float]:
    return narration.run(board)


def _summary(t0: float) -> None:
    calls = []
    if RUNS_LOG.exists():
        for line in RUNS_LOG.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("run_id") == RUN_ID:
                calls.append(e)
    remote = [c for c in calls if c["provider"] != "local"]
    print(f"\nrun {RUN_ID}: {len(remote)} model call(s), {len(calls) - len(remote)} local render(s), "
          f"{time.perf_counter() - t0:.0f}s wall clock")
    for c in remote:
        print(f"  {c['stage']:<10} {c['artifact']:<18} {c['model']:<38} {c['status']:<6} {c['latency_s']}s")


def main(argv: list[str] | None = None) -> int:
    os.chdir(ROOT)
    p = argparse.ArgumentParser(prog="python -m pipeline", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["film", "radio", "validate", "narration", "keyframes", "music", "shots",
                                       "assemble", "smoke", "costs"])
    p.add_argument("--only", help="comma-separated shot ids for the keyframes stage")
    args = p.parse_args(argv)
    t0 = time.perf_counter()
    try:
        if args.command == "smoke":
            from .tools import smoke

            smoke.run()
            return 0
        if args.command == "costs":
            from .tools import costs

            costs.run()
            return 0
        board = load_storyboard()
        print(f"storyboard OK: '{board['title']}', {len(board['shots'])} shots, language {board['language']}")
        if args.command == "validate":
            return 0
        if args.command == "narration":
            narration.run(board)
        elif args.command == "keyframes":
            keyframes.run(board, set(args.only.split(",")) if args.only else None)
        else:
            tl = timeline.build(board, _speech(board), board["providers"]["motion"].get("fps", 24))
            print(f"timeline: {tl['total']:.2f}s ({sum(s['stretched'] for s in tl['shots'])} shot(s) stretched to fit speech)")
            if args.command == "radio":
                music.run(board, tl)
                assemble.radio_cut(board, tl)
            elif args.command == "music":
                music.run(board, tl)
            elif args.command == "shots":
                shots.run(board, tl)
            elif args.command == "assemble":
                assemble.run(board, tl)
            elif args.command == "film":
                keyframes.run(board)
                music.run(board, tl)
                shots.run(board, tl)
                assemble.run(board, tl)
                from .tools import costs

                costs.run(quiet=True)
    except PermanentError as exc:
        print(f"\nstopped: {exc}", file=sys.stderr)
        _summary(t0)
        return 2
    _summary(t0)
    print(f"outputs in {OUTPUTS.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

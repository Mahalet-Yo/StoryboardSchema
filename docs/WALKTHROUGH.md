# Walkthrough script (under 5 minutes)

**0:00–0:30, the film.** Play 15 s of `outputs/final/film.vertical.mp4`. One sentence: "A daughter carries her father's blessing through his death into her life, in Amharic, made by a pipeline from one JSON file."

**0:30–1:45, the architecture.** Open `storyboard.json`: show one shot's `reason`, `keyframe_prompt`, `seed`, `narration_am`. Then show the diagram in `ARCHITECTURE.md`. Make three points:
- The storyboard is the only contract between stages.
- Every file has a `.meta.json` with the hash of its inputs, which is how a re-run knows what changed.
- Every model call is a line in `runs.jsonl`.

Briefly show `make test` passing and the CI badge.

**1:45–2:45, one hard decision.** Choose one:
- **(a) The safety filter.** It refused 6 of 35 image calls. Shot 1 became an insert of hands and water, and the filter turned out not to be deterministic (E5), so the code now reseeds. Show the `seed_used: 1103` sidecar.
- **(b) Ducking.** Show the E8 table: the brief's setting beat my guess, 11.5 dB against 4.8 dB.

**2:45–4:30, regenerate one shot live.**
1. In `storyboard.json`, change shot 6's `keyframe_prompt`, for example "…looking softly upward" → "…looking at an old photograph of her father in her hands".
2. Run `make validate`, then `make film`. You may pause the recording while it runs (about 3.5 min, mostly re-exporting).
3. Show the summary at the end: `2 model call(s)` (shot_06.v and shot_06.h) and nothing else.
4. Run `grep <run_id> runs.jsonl` to show the same from the log, then play shot 6 in the new film.

**4:30–5:00, close.** Name one thing learned, then commit the change with its reason.

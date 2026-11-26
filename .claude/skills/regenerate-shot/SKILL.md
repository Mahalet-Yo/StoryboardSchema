---
name: regenerate-shot
description: Change one shot of the film (keyframe prompt, motion, or narration line) in storyboard.json, regenerate only that shot, and show from runs.jsonl that nothing else was called. Use when asked to "change shot N", "redo the narration for shot N", or to demonstrate caching.
---

# Regenerate one shot

1. **Pick the field.** A picture change is `shots[i].keyframe_prompt` (2 image calls: 9:16 and 16:9). A voice change is `shots[i].narration_am` plus its subtitle `narration_en` (1 TTS call). A new performance of the same line is `narration_take` + 1. A camera change is `camera_move` (no model call, just a local re-render).
2. **Edit `storyboard.json`.** Keep the character wording and the style block out of the shot prompt; the stage adds them.
3. Run `make validate`. Fix anything it reports before going on.
4. Run `make film`. The summary printed at the end lists this run's model calls.
5. **Prove it.** Show the summary, or the log lines for the run:
   ```bash
   RUN=$(tail -1 runs.jsonl | python3 -c "import sys,json;print(json.load(sys.stdin)['run_id'])")
   grep "$RUN" runs.jsonl | grep -v '"provider": "local"'
   ```
   Only the edited shot's artifacts should appear.
6. **Record it.** If the edit tested an idea, add an EXPERIMENTS.md entry. If it answered user feedback, add it to DESIGN.md §6. Commit with a message saying why.

Quota note: TTS free tier is about 10 requests a day and 3 per minute. Never regenerate all narration to test one line.

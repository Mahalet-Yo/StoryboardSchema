# Working in this repository (for coding agents and people)

This file is read by OpenCode, Antigravity CLI and Claude Code (through `CLAUDE.md`). It is the short version of how the project works, plus the rules an agent must follow here.

## What this is
A pipeline that turns `storyboard.json` into a 60–90 s film in two aspect ratios. The storyboard is the only contract between stages, and each stage is one module in `pipeline/`. Read `ARCHITECTURE.md` before changing a stage.

## Commands
- `make film`: everything; cached, so it is cheap to re-run
- `make validate`: run after **every** edit to `storyboard.json` or `schema/`
- `make test`: offline tests; must pass before any commit
- `.venv/bin/ruff check pipeline tests`: lint, as in CI
- `make smoke`: one call per provider; spends a little quota

## Rules
1. **Prompts, seeds, models and mix settings belong in `storyboard.json`, never in code.** If a stage needs a new knob, add it to the schema first, then read it from the storyboard.
2. **Every model call goes through `common.call_with_retry`.** That is what gives it retries, the quota rules and a `runs.jsonl` line. Never call a provider directly.
3. **Every artifact is written with `write_artifact` or `seal`,** with an input hash that covers *everything* that determines it, including the content hash of input files. If you forget an input, stale files will look fresh.
4. **Quota is scarce.**
   - Gemini TTS allows about 10 requests a day; the Lite model allows 3 per minute.
   - Cloudflare's image allowance is ~60 keyframes a day.
   - Do not loop over shots "to test". Use `--only` or edit one shot.
5. **Never print, log or commit secrets.** Keys come from `.env` (git-ignored) via `common.require_env`. `common.redact` scrubs logs, and `tests/test_repo_hygiene.py` scans tracked files.
6. **Real people need consent first.** Adding a character requires a `consent` record. A real person needs `basis: consent_on_file` and an entry in `ETHICS.md` *before* generating anything of them. The cross-check will refuse otherwise; do not bypass it.
7. **Write down what you learn.**
   - A failure goes in `FAILURES.md`.
   - A change made to test a hypothesis goes in `EXPERIMENTS.md` (hypothesis, change, result, evidence).
   - A user-test change goes in `DESIGN.md`.
   - Cite `runs.jsonl` lines or files as evidence, and do not invent results.
8. **Commits are small and separate:** one concern each, with a message saying why.

## Where things are
| Need | Look at |
|---|---|
| change the story or a shot | `storyboard.json` (then `make validate`) |
| the contract's shape | `schema/storyboard.schema.json`, `common.cross_check` |
| caching / retry / log rules | `pipeline/common.py` |
| a provider's request shape | `_synthesise` (narration), `_generate` (keyframes), `_ace_step` (music) |
| mix and export | `pipeline/assemble.py` |
| measured numbers | `runs.jsonl`, `outputs/**/*.meta.json`, `outputs/final/qc.json` |

## Skills
- `.claude/skills/regenerate-shot/`: change one shot, regenerate only it, and prove it from the log (the walkthrough's live step).

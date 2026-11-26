# One command: `make film` regenerates the whole film from storyboard.json.
# Only what changed since the last run is regenerated (see ARCHITECTURE.md, Caching).
PY := .venv/bin/python
RUN := $(PY) -m pipeline

.PHONY: setup film radio validate narration keyframes music shots assemble smoke costs duck-sweep test clean-final

setup: .venv/.ok
.venv/.ok: requirements.txt
	python3 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt
	@touch $@

film: setup        ## storyboard -> outputs/final/film.{vertical,horizontal}.mp4
	$(RUN) film
radio: setup       ## narration + score over black (Phase 1 prototype)
	$(RUN) radio
validate narration keyframes music shots assemble smoke costs: setup
	$(RUN) $@
duck-sweep: setup  ## experiment E8: measure ducking settings on the real narration
	$(PY) -m pipeline.tools.duck_sweep
test: setup
	$(PY) -m pytest -q
clean-final:       ## force the edit to re-render (keeps every model output)
	rm -rf outputs/final outputs/audio

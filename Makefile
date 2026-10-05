PY ?= python
.PHONY: setup demo train benchmark report dashboard test all
setup:
	$(PY) -m pip install -e ".[rl,dev]"
test:
	$(PY) -m pytest -q -m "not slow"
demo:
	$(PY) scripts/make_media.py && $(PY) scripts/make_assets.py
train:
	$(PY) scripts/train_ppo.py
	$(PY) scripts/run_lesion_sweep.py 5
benchmark:
	$(PY) scripts/run_benchmark.py
report:
	$(PY) scripts/make_report.py
dashboard:
	$(PY) scripts/make_readme.py && cd dashboard && npm install && npm run build
all: setup test demo benchmark report dashboard

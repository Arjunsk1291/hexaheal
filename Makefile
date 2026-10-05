PY ?= python
.PHONY: setup demo train benchmark report dashboard test all
setup:
	$(PY) -m pip install -e ".[rl,dev]"
test:
	$(PY) -m pytest -q -m "not slow"
demo:
	$(PY) scripts/make_demo.py
train:
	$(PY) scripts/train_ppo.py --max-hours 1.5 --seeds 1
	$(PY) scripts/run_connectome_setup.py
benchmark:
	$(PY) scripts/run_benchmark.py
report:
	$(PY) scripts/make_report.py
dashboard:
	$(PY) scripts/export_dashboard_data.py && cd dashboard && npm install && npm run build
all: setup test demo benchmark report dashboard

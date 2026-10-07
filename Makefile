PY ?= python3
.PHONY: test reproduce-v4
test:
	PYTHONPATH=src $(PY) -m pytest -q -m "not slow"
reproduce-v4:
	bash scripts/reproduce_v4.sh tables

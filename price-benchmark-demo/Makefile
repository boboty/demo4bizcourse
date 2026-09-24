PYTHON ?= .venv/bin/python

.PHONY: dev test
.venv/.installed: requirements.txt
	@python3.12 -m venv .venv
	@.venv/bin/python -m pip install -r requirements.txt
	@touch .venv/.installed

dev: .venv/.installed
	@$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000

test: .venv/.installed
	@$(PYTHON) -m pytest -q

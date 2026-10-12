.PHONY: setup dev test validate reset export-students
setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt
dev:
	.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port $${PORT:-8016}
test:
	.venv/bin/python -m pytest -q
validate:
	.venv/bin/python scripts/validate_demo.py
reset:
	.venv/bin/python scripts/reset_demo.py
export-students:
	.venv/bin/python scripts/export_student_packages.py

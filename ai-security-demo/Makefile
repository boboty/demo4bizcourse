.PHONY: setup dev test check
setup:
	uv sync --python 3.12
dev:
	uv run --offline uvicorn app.main:app --host 127.0.0.1 --port 8016
test:
	uv run --offline pytest -q
check:
	uv run --offline ruff check app tests scripts
	uv run --offline pyright
	uv run --offline pytest -q

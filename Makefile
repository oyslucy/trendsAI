.PHONY: setup lint test run dashboard

DATE ?= $(shell date +%Y-%m-%d)

setup:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src

test:
	uv run pytest

run:
	uv run consumer-signal --date $(DATE)

dashboard:
	uv run uvicorn dashboard.app:app --reload

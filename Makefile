.DEFAULT_GOAL := help

VIEWER_PORT ?= 7070

.PHONY: help install run viewer sessions session fmt lint check test clean

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  install          Install dependencies (creates .venv via uv)"
	@echo "  hooks            Install pre-commit hooks into .git/hooks"
	@echo "  run              Start the chat REPL"
	@echo "  viewer           Start the session debug viewer  (http://127.0.0.1:$(VIEWER_PORT)/)"
	@echo "  viewer PORT=8080 Start viewer on a custom port"
	@echo "  sessions         List all saved sessions (CLI)"
	@echo "  session ID=<id>  Inspect a specific session (CLI)"
	@echo "  fmt              Format code with ruff"
	@echo "  lint             Lint code with ruff"
	@echo "  check            Run fmt + lint"
	@echo "  test             Run pytest"
	@echo "  clean            Remove .venv, __pycache__, and saved sessions"
	@echo "  clean-sessions   Remove only saved sessions from ~/.claw/sessions/"

install:
	uv sync

hooks:
	uv run pre-commit install

run:
	uv run claw

viewer:
	uv run python -m claw_code_python.viewer --serve --port $(VIEWER_PORT)

sessions:
	uv run python -m claw_code_python.viewer

session:
	@if [ -z "$(ID)" ]; then \
		echo "Usage: make session ID=<session-id>"; exit 1; \
	fi
	uv run python -m claw_code_python.viewer $(ID)

fmt:
	uv run ruff format .

lint:
	uv run ruff check .

check: fmt lint

test:
	uv run pytest -v

clean: clean-sessions
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete

clean-sessions:
	rm -rf ~/.claw/sessions/

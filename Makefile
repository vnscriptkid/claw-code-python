.DEFAULT_GOAL := help

.PHONY: help install run fmt lint check clean

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  install   Install dependencies (creates .venv via uv)"
	@echo "  run       Start the chat REPL"
	@echo "  fmt       Format code with ruff"
	@echo "  lint      Lint code with ruff"
	@echo "  check     Run fmt + lint"
	@echo "  clean     Remove .venv and __pycache__"

install:
	uv sync

run:
	uv run claw

fmt:
	uv run ruff format .

lint:
	uv run ruff check .

check: fmt lint

clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete

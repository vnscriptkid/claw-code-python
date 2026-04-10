# claw-code-python

A Python rebuild of the [claw-code](../claw-code) coding agent — built incrementally across 10 steps to demonstrate how coding agents work from the ground up.

Each step adds one capability and produces a fully working agent.

| Step | Capability |
|------|-----------|
| **1** | Minimal LLM chat loop (this step) |
| 2 | Tool definitions + agent loop |
| 3 | File system tools |
| 4 | Shell execution |
| 5 | Search tools (glob + grep) |
| 6 | System prompt + project context |
| 7 | Session persistence |
| 8 | Permission system |
| 9 | Conversation compaction |
| 10 | Streaming + rich terminal UI |

---

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An [Anthropic API key](https://console.anthropic.com/)

Install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Setup

```bash
# 1. Clone / enter the project
cd claw-code-python

# 2. Copy the env template and add your API key
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# 3. Install dependencies and create the virtual environment
make install
```

---

## Running

```bash
# Start the chat REPL
make run

# Or use the installed entry-point directly
uv run claw
```

Type your message and press Enter. Type `exit` or press `Ctrl-D` to quit.

```
claw-code-python  (step 1 — minimal chat loop)
Type "exit" or press Ctrl-D to quit.

you> what's the capital of France?
claude> The capital of France is Paris.

[42 in / 12 out | ~$0.0001]
```

---

## Development

```bash
make install      # install / sync dependencies
make run          # run the agent
make fmt          # format code with ruff
make lint         # lint with ruff
make check        # fmt + lint
make clean        # remove .venv and caches
```

---

## Project layout

```
claw-code-python/
├── claw_code_python/
│   ├── __init__.py
│   ├── main.py          # REPL loop
│   ├── llm_client.py    # Anthropic API client
│   └── models.py        # Message / response types
├── .env.example         # env var template
├── pyproject.toml       # project metadata + dependencies
├── uv.lock              # locked dependency versions
└── Makefile
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | — | Your Anthropic API key |
| `CLAW_MODEL` | ❌ | `claude-haiku-4-5` | Model to use |

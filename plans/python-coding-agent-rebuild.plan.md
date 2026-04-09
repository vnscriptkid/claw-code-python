# Plan: Python Coding Agent Rebuild

> Source PRD: plans/python-coding-agent-rebuild.prd.md

## Architectural decisions

- **Package**: `claw_code_python` Python package, entry point via `main.py`
- **LLM provider**: Anthropic Claude API only (via `anthropic` SDK)
- **Key models**: `Message`, `ContentBlock`, `ToolUse`, `ToolResult`, `Usage` in `models.py`
- **Tool interface**: Abstract `Tool` base class with `name`, `description`, `input_schema`, `required_permission`, `execute(input: dict) -> str`
- **Agent loop contract**: `run_turn(messages) -> messages` loops internally until LLM response has no `tool_use` blocks
- **Session storage**: `~/.claw/sessions/<uuid>.jsonl`, one JSON object per line
- **Permission levels**: `ReadOnly < WorkspaceWrite < FullAccess` (ascending privilege)
- **Token estimation**: ~4 chars per token heuristic; compaction triggers at 80% of context window
- **Target Python**: 3.11+
- **Dependencies**: `anthropic`, `rich`, `pydantic`; stdlib only for file I/O, subprocess, glob, re

---

## Phase 1: Minimal LLM chat loop

**User stories**: 1, 2, 3, 4

### What to build

A working REPL that reads user input, sends it to the Anthropic API, prints the response, and shows token usage after each turn. The API key comes from the `ANTHROPIC_API_KEY` environment variable. No tools, no agent loop — just the basic request/response cycle end-to-end across `main.py`, `llm_client.py`, and `models.py`.

### Acceptance criteria

- [ ] `python -m claw_code_python` starts a REPL that accepts user input
- [ ] Each user message is sent to the Anthropic API and the response is printed
- [ ] Token usage (input, output, total) is printed after each response
- [ ] Missing `ANTHROPIC_API_KEY` prints a clear error and exits
- [ ] The raw message format (roles, content blocks) is visible in a debug mode or documented in code comments

---

## Phase 2: Tool abstraction + agent loop

**User stories**: 5, 6, 7, 8

### What to build

Introduce the `Tool` base class in `tools/base.py`, a `ToolRegistry` in `tool_registry.py`, and a `Calculator` demo tool in `tools/calculator.py`. Wire up `agent_loop.py` so `run_turn()` sends messages, detects `tool_use` blocks, dispatches to the registry, appends `tool_result` blocks, and loops until the LLM responds with no tool calls.

### Acceptance criteria

- [ ] `Tool` base class defines `name`, `description`, `input_schema`, and `execute(input) -> str`
- [ ] `ToolRegistry` registers tools by name and dispatches calls by name
- [ ] `Calculator` tool supports add, subtract, multiply, divide
- [ ] Agent loop sends tool results back to the LLM and continues looping
- [ ] Loop terminates when LLM response contains no `tool_use` blocks
- [ ] Asking "what is 123 * 456?" causes the agent to call the calculator and return the answer

---

## Phase 3: File operation tools

**User stories**: 9, 10, 11, 12, 13, 14

### What to build

Add `read_file`, `write_file`, and `edit_file` tools in `tools/`. Implement path validation that rejects paths outside the workspace directory. `read_file` returns contents with line numbers and supports `offset`/`limit`; it detects binary files and returns an error message instead of garbled output. `write_file` enforces a size limit. `edit_file` requires the target string to appear exactly once.

### Acceptance criteria

- [ ] `read_file` returns file contents with line numbers prefixed
- [ ] `read_file` accepts optional `offset` and `limit` parameters
- [ ] `read_file` returns a descriptive error for binary files instead of raw bytes
- [ ] `write_file` creates or overwrites a file; rejects content exceeding the size limit
- [ ] `edit_file` replaces an exact string in a file
- [ ] `edit_file` fails with a clear error if the target string appears 0 or 2+ times
- [ ] All three tools reject paths outside the workspace directory

---

## Phase 4: Shell + search tools

**User stories**: 15, 16, 17, 18, 19, 20, 21

### What to build

Add a `bash` tool in `tools/bash.py` that executes shell commands, captures stdout and stderr, enforces a configurable timeout (killing the process on expiry), and truncates very large outputs. Add `glob_search` in `tools/glob_search.py` that finds files by glob pattern, respects `.gitignore`, and skips hidden directories by default. Add `grep_search` in `tools/grep_search.py` that searches file contents by regex with context lines and supports output modes (matching lines, file paths only, match counts).

### Acceptance criteria

- [ ] `bash` returns combined stdout and stderr
- [ ] `bash` kills the subprocess and returns an error after the timeout expires
- [ ] `bash` truncates output that exceeds the max size with a truncation notice
- [ ] `glob_search` returns file paths matching a glob pattern recursively
- [ ] `glob_search` excludes files matched by `.gitignore` and skips hidden directories by default
- [ ] `grep_search` returns matching lines with configurable before/after context
- [ ] `grep_search` supports `content`, `files_with_matches`, and `count` output modes

---

## Phase 5: Dynamic system prompt

**User stories**: 23, 24, 25, 26

### What to build

Add `prompt.py` and `git_context.py`. `prompt.py` assembles the system prompt at startup from modular sections: base agent instructions, current date/CWD/OS, tool documentation, git context, and any `CLAUDE.md` / `AGENTS.md` files discovered by walking the project directory tree. `git_context.py` extracts current branch, status, and recent commits via subprocess.

### Acceptance criteria

- [ ] System prompt includes current date, working directory, and OS at startup
- [ ] System prompt includes a summary of all registered tools
- [ ] `CLAUDE.md` and `AGENTS.md` files found anywhere in the project tree are injected into the system prompt
- [ ] Git branch, status summary, and recent commits are included when the CWD is inside a git repo
- [ ] Each section of the system prompt can be assembled and inspected independently

---

## Phase 6: Session persistence

**User stories**: 27, 28, 29, 30

### What to build

Add `session.py`. After each turn, the full conversation is appended to `~/.claw/sessions/<uuid>.jsonl` (one JSON object per line). Add `--resume <session-id>` CLI flag to load a prior session and continue it. Add `--list` CLI flag to print past sessions with their ID, timestamps, and cumulative token usage. Store session metadata (ID, created/updated timestamps, token totals) alongside the JSONL.

### Acceptance criteria

- [ ] Conversation is saved to `~/.claw/sessions/<uuid>.jsonl` after each turn
- [ ] All content block types (text, tool_use, tool_result) round-trip cleanly through JSONL serialization
- [ ] `--resume <session-id>` restores the prior conversation and continues the REPL
- [ ] `--list` prints all sessions with ID, created time, last updated time, and total tokens used
- [ ] Session metadata is updated after each turn

---

## Phase 7: Permission system

**User stories**: 31, 32, 33, 34

### What to build

Add `permissions.py` defining three modes: `ReadOnly`, `WorkspaceWrite`, `FullAccess`. Each `Tool` declares its `required_permission`. Before dispatching any tool call, the agent loop checks the current mode against the tool's requirement. If the mode is insufficient, the user is prompted interactively to approve or deny. A denial returns a structured error string to the LLM so it can respond gracefully.

### Acceptance criteria

- [ ] `ReadOnly` permits only `read_file`, `glob_search`, `grep_search`
- [ ] `WorkspaceWrite` additionally permits `write_file`, `edit_file`
- [ ] `FullAccess` additionally permits `bash` and `calculator`
- [ ] The agent prompts the user for approval when a tool requires higher permission than the active mode
- [ ] User approval elevates permission for that call only (not permanently)
- [ ] User denial causes the agent loop to return a structured error to the LLM
- [ ] Permission check is centralized in the agent loop / permission module, not in individual tools

---

## Phase 8: Compaction + Streaming UI

**User stories**: 35, 36, 37, 38, 39, 40, 41, 42, 43

### What to build

Add `compact.py` for context compaction: estimate token usage with a character-count heuristic, trigger compaction when usage exceeds 80% of the model's context window, send older messages to the LLM for summarization, replace them with the summary, and preserve recent messages verbatim. Show a `[compacted]` notice in the UI when this occurs.

Add `streaming.py` for SSE parsing: handle all Anthropic streaming event types, print text deltas immediately, accumulate tool input JSON, and assemble the full response on `message_stop`.

Add `ui.py` using the Rich library: render markdown in LLM responses, display tool calls in panels with a spinner while executing, and show token usage after each turn.

### Acceptance criteria

- [ ] Compaction is triggered automatically when estimated token usage exceeds 80% of context window
- [ ] Older messages are replaced with an LLM-generated summary; recent messages are preserved verbatim
- [ ] A `[compacted]` notice is shown in the terminal when compaction occurs
- [ ] LLM responses stream token-by-token; text appears as it is generated
- [ ] Tool calls are displayed with a spinner while executing
- [ ] LLM response text is rendered as markdown (code blocks, lists, headings)
- [ ] Token usage is displayed after each turn in the Rich UI

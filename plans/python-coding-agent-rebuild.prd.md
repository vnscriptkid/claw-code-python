# PRD: Python Coding Agent Rebuild

## Problem Statement

The existing `claw-code` coding agent is implemented in Rust, which makes it difficult to understand, extend, or experiment with the core agentic patterns. There is no Python reference implementation, so developers who want to learn how a coding agent works — or who want to build their own agent in Python — have no clear starting point that demonstrates the incremental architecture from a simple LLM chat loop up to a fully featured coding agent.

The goal is to rebuild the coding agent from scratch in Python, one capability at a time, so that each step produces a working, runnable version. This gives the developer hands-on understanding of how each layer of a coding agent works, and produces a Python codebase that can serve as a foundation for future experimentation.

## Solution

Build a Python coding agent (`claw-code-python`) incrementally across 10 steps. Each step produces a fully working version of the agent. Each step adds exactly one new capability, building directly on the previous step. The final product is a complete coding agent with streaming output, rich terminal UI, and all the core capabilities of the Rust original: chat, file operations, shell execution, code search, system prompt assembly, session persistence, permissions, and context compaction.

The Rust implementation serves as the reference architecture throughout. Each step maps to a specific module in the Rust source.

## User Stories

1. As a developer learning about AI agents, I want to run a minimal LLM chat loop in Python, so that I can understand the basic request/response cycle before adding any complexity.
2. As a developer, I want to see the exact message format (roles, content blocks, tokens) sent to and received from the Anthropic API, so that I understand the protocol underlying all agent behavior.
3. As a developer, I want API key management handled via environment variables, so that I can run the agent without hardcoding credentials.
4. As a developer, I want to see token usage printed after each response, so that I develop cost awareness from the very beginning.
5. As a developer, I want to define tools using a base class with a name, description, input schema, and execute method, so that I understand the tool abstraction pattern.
6. As a developer, I want to register tools in a central registry and dispatch calls by name, so that the agent loop remains decoupled from individual tool implementations.
7. As a developer, I want to observe the full agent loop — LLM responds with tool_use, tool executes, result feeds back, loop continues — using a simple calculator demo, so that I understand the core agentic pattern before adding real tools.
8. As a developer, I want the agent loop to terminate naturally when the LLM returns a response with no tool calls, so that I understand the stopping condition for agentic execution.
9. As a developer, I want a `read_file` tool that returns file contents with line numbers and optional offset/limit, so that the agent can inspect specific regions of large files.
10. As a developer, I want the `read_file` tool to detect binary files and return an appropriate message instead of garbled output, so that the agent handles non-text files gracefully.
11. As a developer, I want a `write_file` tool that writes content to a path with size limit validation, so that the agent can create or overwrite files safely.
12. As a developer, I want an `edit_file` tool that finds an exact string and replaces it, so that the agent can make targeted edits without rewriting entire files.
13. As a developer, I want the `edit_file` tool to fail if the target string appears more than once, so that ambiguous edits are caught before they corrupt a file.
14. As a developer, I want path validation that prevents file operations outside the workspace directory, so that the agent cannot escape its working directory.
15. As a developer, I want a `bash` tool that executes shell commands and returns stdout and stderr, so that the agent can run tests, check git status, and install dependencies.
16. As a developer, I want the `bash` tool to enforce a configurable timeout and kill the process if it exceeds it, so that runaway commands do not block the agent indefinitely.
17. As a developer, I want the `bash` tool to truncate very large outputs, so that the LLM context window is not exhausted by a single command.
18. As a developer, I want a `glob_search` tool that finds files matching a glob pattern recursively, so that the agent can navigate unfamiliar codebases without guessing file paths.
19. As a developer, I want the `glob_search` tool to respect `.gitignore` and skip hidden directories by default, so that results are focused on relevant project files.
20. As a developer, I want a `grep_search` tool that searches file contents by regex and returns matching lines with context, so that the agent can locate specific code across an entire project.
21. As a developer, I want `grep_search` to support output modes (matching lines, file paths only, match counts), so that the agent can tailor search output to the task.
22. As a developer, I want the MVP coding agent (Steps 1–5) to be fully functional for real coding tasks, so that I have a usable baseline before adding enhancement features.
23. As a developer, I want the system prompt assembled dynamically at startup, so that it includes the current date, working directory, OS, and agent instructions.
24. As a developer, I want the agent to discover and inject `CLAUDE.md` and `AGENTS.md` files from the project directory tree, so that it picks up project-specific conventions automatically.
25. As a developer, I want git context (current branch, status, recent commits) injected into the system prompt, so that the agent is aware of the repository state without being asked.
26. As a developer, I want the system prompt builder to be modular, so that each context section (base instructions, tool docs, git context, project files) can be assembled and tested independently.
27. As a developer, I want conversation sessions saved to disk as JSONL files after each turn, so that no work is lost if the process crashes.
28. As a developer, I want to resume a previous session using `--resume <session-id>`, so that I can continue work across multiple terminal sessions.
29. As a developer, I want to list past sessions using `--list`, so that I can find the session ID I want to resume.
30. As a developer, I want session metadata (session ID, created time, updated time, cumulative token usage) stored alongside the conversation, so that I can track usage and find relevant sessions.
31. As a developer, I want a permission system with three modes — read-only, workspace-write, and full-access — so that the agent's capabilities can be scoped to the level of trust appropriate for a given context.
32. As a developer, I want each tool to declare its required permission level, so that the permission check is centralized and tools do not implement their own authorization logic.
33. As a developer, I want the agent to prompt me interactively when a tool requires a higher permission level than the current mode, so that I can approve or deny elevated operations at runtime.
34. As a developer, I want the agent to return a structured error to the LLM when I deny a permission request, so that the LLM can respond gracefully instead of hanging.
35. As a developer, I want automatic conversation compaction triggered when estimated token usage exceeds a threshold, so that long sessions do not crash or lose context.
36. As a developer, I want the compaction algorithm to summarize older messages using the LLM itself, so that the summary captures intent and outcomes rather than just truncating.
37. As a developer, I want recent messages preserved verbatim after compaction, so that the LLM retains full context for the current task.
38. As a developer, I want a `[compacted]` notice shown in the UI when compaction occurs, so that I understand why earlier context is missing.
39. As a developer, I want LLM responses streamed token-by-token using SSE, so that I see output as it is generated rather than waiting for the full response.
40. As a developer, I want a rich terminal UI using the Rich library, so that agent output is readable, well-formatted, and clearly separates assistant text from tool call panels.
41. As a developer, I want tool calls displayed with a spinner while executing, so that I can see what the agent is doing in real time.
42. As a developer, I want markdown in LLM responses rendered in the terminal, so that code blocks, lists, and headings are properly formatted.
43. As a developer, I want token usage displayed after each turn, so that I always know how much context has been consumed.

## Implementation Decisions

### Module Structure

The project is organized as a Python package `claw_code_python` with the following top-level modules:

- `main.py` — CLI entry point: REPL loop, argument parsing, session wiring
- `llm_client.py` — Anthropic API client: sends message requests, returns responses
- `models.py` — Core data types: Message, ContentBlock, ToolUse, ToolResult, Usage
- `agent_loop.py` — Core agent loop: `run_turn()` sends messages, dispatches tool calls, feeds results back, loops until no tool calls remain
- `tool_registry.py` — Tool registration and dispatch by name
- `prompt.py` — System prompt assembly: base instructions, project files, git context, environment
- `git_context.py` — Git status, branch, recent commits extraction via subprocess
- `session.py` — Session persistence: JSONL save/load, session listing, metadata
- `permissions.py` — Permission modes, per-tool authorization, interactive prompter
- `compact.py` — Token estimation, compaction trigger, LLM summarization, session rebuild
- `streaming.py` — SSE event parser, delta accumulator, response assembly from stream
- `ui.py` — Rich-based terminal rendering: markdown, tool panels, spinners, usage display
- `tools/base.py` — Abstract `Tool` base class
- `tools/calculator.py` — Demo tool (addition, subtraction, multiplication, division)
- `tools/read_file.py`, `write_file.py`, `edit_file.py` — File operation tools
- `tools/bash.py` — Shell execution tool
- `tools/glob_search.py`, `grep_search.py` — Search tools

### Agent Loop Contract

The `run_turn()` function takes the current message list and returns an updated message list. It loops internally until the LLM response contains no `tool_use` blocks. Each iteration: send messages to LLM, parse response, execute all tool calls in the response, append `tool_result` blocks, repeat.

### Tool Interface

Each tool is a class with:
- `name: str` — unique identifier matching the tool name in LLM requests
- `description: str` — shown to the LLM in tool definitions
- `input_schema: dict` — JSON Schema object for tool input validation
- `required_permission: PermissionLevel` — minimum permission mode required
- `execute(input: dict) -> str` — runs the tool and returns a string result

### Message Serialization

Messages are serialized to JSONL (one JSON object per line) for session persistence. The format must round-trip cleanly for all content block types: text, tool_use, tool_result, and image (reserved for future use).

### Permission Modes

Three modes in ascending order of privilege:
1. `ReadOnly` — allows: read_file, glob_search, grep_search
2. `WorkspaceWrite` — adds: write_file, edit_file
3. `FullAccess` — adds: bash, calculator (and future: Agent, WebFetch)

### Compaction Strategy

Token estimation uses a character-count heuristic (approx 4 chars per token). Compaction is triggered when estimated usage exceeds 80% of the model's context window. The strategy: split messages at a fixed keep-recent boundary, send the older portion to the LLM as a summarization request, replace those messages with the summary, prepend a continuation preamble to the kept messages.

### Streaming

SSE parsing handles the Anthropic streaming event types: `message_start`, `content_block_start`, `content_block_delta` (text_delta and input_json_delta), `content_block_stop`, `message_delta`, `message_stop`. Text deltas are printed immediately. Tool input JSON is accumulated and parsed on `content_block_stop`.

### LLM Provider

Anthropic Claude API only for Steps 1–10. Multi-provider support is out of scope for this PRD.

### Dependencies

- `anthropic` — official Anthropic Python SDK (replaces raw httpx)
- `rich` — terminal UI (Step 10)
- `pydantic` — data validation for models
- Python stdlib only for file I/O, subprocess, glob, re

## Out of Scope

- Multi-provider support (OpenAI, xAI, etc.)
- Configuration file system (user-level or project-level config files)
- Hook system (pre/post tool-use hooks)
- MCP (Model Context Protocol) integration
- Sub-agent spawning (delegating tasks to child agents)
- Web tools (WebFetch, WebSearch)
- Plugin system for third-party tool loading
- Full subprocess sandboxing or container isolation for bash
- Image content blocks (beyond reserving the type)
- Windows support (bash tool assumes POSIX)
- Tests or CI pipeline (this is a learning project)

## Further Notes

- Each of the 10 steps maps directly to a module or set of modules in the Rust source. The Rust implementation is the canonical reference for behavior; the Python implementation is allowed to simplify where the Rust version is complex for Rust-specific reasons (e.g., ownership, async runtime).
- Steps 1–5 constitute the minimum viable coding agent. Steps 6–10 are enhancements. A developer can stop at any step and have a working, useful tool.
- The incremental structure is intentional: each step should take a few hours to implement, and should be completable before moving on. The plan is also a learning curriculum, not just a build plan.
- Session files are stored in `~/.claw/sessions/` as `<uuid>.jsonl`.
- The project targets Python 3.11+ to use modern type annotation syntax and `tomllib` from stdlib.

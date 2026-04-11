"""Session viewer -- HTTP debug UI for inspecting saved sessions.

Usage:
    python -m claw_code_python.viewer                     # list sessions (CLI)
    python -m claw_code_python.viewer <session_id>        # inspect one session (CLI)
    python -m claw_code_python.viewer --serve             # start HTTP server (default port 7070)
    python -m claw_code_python.viewer --serve --port 8080

HTTP routes:
    GET /           -> session list page
    GET /<id>       -> session detail (full turn-by-turn replay)
    GET /api/<id>   -> raw records as JSON array
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from .session import Session, LoadedSession

# ── CSS ────────────────────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  background: #0d1117; color: #e6edf3;
  padding: 32px 24px; max-width: 1000px; margin: 0 auto;
}
h1 { color: #58a6ff; margin-bottom: 8px; font-size: 1.4rem; }
h2 { color: #8b949e; margin-bottom: 16px; font-size: .85rem;
     letter-spacing: .07em; text-transform: uppercase; }
a { color: #58a6ff; text-decoration: none; }
a:hover { text-decoration: underline; }
p { color: #8b949e; font-size: .9rem; }

/* ── Session list ── */
.session-list { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }
.session-card {
  background: #161b22; border: 1px solid #30363d; border-radius: 8px;
  padding: 14px 18px; transition: border-color .15s;
}
.session-card:hover { border-color: #58a6ff; }
.session-id { font-weight: bold; font-size: .95rem; }
.session-meta { font-size: .75rem; color: #8b949e; margin-top: 5px; }

/* ── Navigation ── */
.nav { margin-bottom: 20px; font-size: .82rem; color: #8b949e; }
.nav a { margin-right: 14px; }

/* ── Session header ── */
.session-header { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                  padding: 14px 18px; margin-bottom: 24px; font-size: .82rem; }
.session-header strong { color: #e6edf3; }

/* ── Collapsible turns ── */
.expand-controls { margin-bottom: 16px; display: flex; gap: 10px; }
.expand-controls button {
  background: #21262d; border: 1px solid #30363d; border-radius: 6px;
  color: #adbac7; font-family: inherit; font-size: .78rem;
  padding: 4px 12px; cursor: pointer; transition: border-color .15s;
}
.expand-controls button:hover { border-color: #58a6ff; color: #58a6ff; }

.turn { margin-bottom: 10px; }
details.turn-details {
  background: #161b22; border: 1px solid #30363d;
  border-radius: 8px; overflow: hidden;
}
details.turn-details[open] { border-color: #388bfd; }
details.turn-details > summary {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 14px; cursor: pointer; list-style: none;
  font-size: .78rem; color: #8b949e; user-select: none;
  transition: background .12s;
}
details.turn-details > summary::-webkit-details-marker { display: none; }
details.turn-details > summary::marker { display: none; }
details.turn-details > summary:hover { background: #1c2128; }
details.turn-details[open] > summary { border-bottom: 1px solid #30363d; }
.turn-chevron {
  flex-shrink: 0; color: #58a6ff; font-size: .7rem; width: 14px;
  transition: transform .15s;
}
details.turn-details[open] .turn-chevron { transform: rotate(90deg); }
.turn-seq { font-weight: bold; color: #58a6ff; font-size: .88rem; min-width: 56px; }
.turn-ts  { flex: 1; }
.turn-preview { color: #6e7681; font-size: .75rem; max-width: 320px;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.turn-body { padding: 12px 14px; }
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: .7rem; font-weight: bold; letter-spacing: .03em;
}
.badge-in  { background: #1a3a28; color: #3fb950; }
.badge-out { background: #152740; color: #58a6ff; }

/* ── Messages ── */
.msg { border-radius: 6px; padding: 10px 14px; margin-bottom: 6px;
       font-size: .84rem; line-height: 1.6; }
.msg-user      { background: #1c2128; border-left: 3px solid #3fb950; }
.msg-assistant { background: #1c2128; border-left: 3px solid #58a6ff; }
.msg-role { font-size: .68rem; font-weight: bold; letter-spacing: .1em;
            text-transform: uppercase; margin-bottom: 6px; }
.msg-user      .msg-role { color: #3fb950; }
.msg-assistant .msg-role { color: #58a6ff; }

/* ── Content blocks ── */
.block-text { white-space: pre-wrap; word-break: break-word; }

.tool-use {
  background: #1e1a15; border: 1px solid #d29922; border-radius: 6px;
  padding: 10px 14px; margin: 4px 0; font-size: .8rem;
}
.tool-use-header { display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px; }
.tool-use-name   { color: #d29922; font-weight: bold; font-size: .88rem; }
.tool-use-id     { color: #8b949e; font-size: .7rem; }

.tool-result {
  background: #141e17; border: 1px solid #3fb950; border-radius: 6px;
  padding: 10px 14px; margin: 4px 0; font-size: .8rem;
}
.tool-result.is-error { background: #1e1417; border-color: #f85149; }
.tool-result-header { display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px; }
.tool-result-label  { font-weight: bold; font-size: .75rem; letter-spacing: .05em; }
.tool-result        .tool-result-label { color: #3fb950; }
.tool-result.is-error .tool-result-label { color: #f85149; }
.tool-result-ref    { color: #8b949e; font-size: .7rem; }
.tool-result-content { white-space: pre-wrap; word-break: break-word; color: #adbac7; }

pre.json {
  background: #161b22; border: 1px solid #30363d; border-radius: 4px;
  padding: 10px; font-size: .78rem; overflow-x: auto; white-space: pre; color: #adbac7;
}

/* ── Tool call summary strip ── */
.tool-strip { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 10px; }
.tool-pill {
  display: inline-flex; align-items: center; gap: 5px;
  background: #21262d; border: 1px solid #30363d; border-radius: 20px;
  padding: 3px 10px; font-size: .72rem; color: #adbac7;
}
.tool-pill.err { border-color: #f85149; color: #f85149; }
"""

# ── HTML helpers ───────────────────────────────────────────────────────────────


def _html(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — claw viewer</title>
<style>{_CSS}</style>
</head>
<body>{body}</body>
</html>"""


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_block(block: dict[str, Any]) -> str:
    t = block.get("type", "")

    if t == "text":
        text = block.get("text", "")
        if not text.strip():
            return ""
        return f'<div class="block-text">{_esc(text)}</div>'

    if t == "tool_use":
        inp_json = json.dumps(block.get("input", {}), indent=2, ensure_ascii=False)
        return (
            f'<div class="tool-use">'
            f'<div class="tool-use-header">'
            f'<span class="tool-use-name">⚙ {_esc(block.get("name", "?"))}</span>'
            f'<span class="tool-use-id">id: {_esc(block.get("id", ""))}</span>'
            f"</div>"
            f'<pre class="json">{_esc(inp_json)}</pre>'
            f"</div>"
        )

    if t == "tool_result":
        is_error = block.get("is_error", False)
        err_cls = " is-error" if is_error else ""
        label = "✗ ERROR" if is_error else "✓ RESULT"
        content = str(block.get("content", ""))
        return (
            f'<div class="tool-result{err_cls}">'
            f'<div class="tool-result-header">'
            f'<span class="tool-result-label">{label}</span>'
            f'<span class="tool-result-ref">← {_esc(block.get("tool_use_id", ""))}</span>'
            f"</div>"
            f'<div class="tool-result-content">{_esc(content)}</div>'
            f"</div>"
        )

    # Fallback: raw JSON
    return f'<pre class="json">{_esc(json.dumps(block, indent=2, ensure_ascii=False))}</pre>'


def _render_message(msg: dict[str, Any]) -> str:
    role = msg.get("role", "?")
    css = "msg-user" if role == "user" else "msg-assistant"
    blocks_html = "".join(_render_block(b) for b in msg.get("content", []))
    if not blocks_html.strip():
        return ""
    return (
        f'<div class="msg {css}"><div class="msg-role">{role}</div>{blocks_html}</div>'
    )


def _render_tool_strip(tool_calls: list[dict[str, Any]]) -> str:
    if not tool_calls:
        return ""
    pills = []
    for tc in tool_calls:
        err_cls = " err" if tc.get("is_error") else ""
        icon = "✗" if tc.get("is_error") else "⚙"
        pills.append(
            f'<span class="tool-pill{err_cls}">{icon} {_esc(tc.get("name", "?"))}</span>'
        )
    return f'<div class="tool-strip">{"".join(pills)}</div>'


# ── Page renderers ─────────────────────────────────────────────────────────────


def render_session_list(sessions: list[dict[str, Any]]) -> str:
    if not sessions:
        body = (
            "<h1>claw sessions</h1>"
            "<p>No sessions found in <code>~/.claw/sessions/</code></p>"
        )
        return _html("sessions", body)

    cards = []
    for s in sessions:
        sid = s.get("session_id", "?")
        model = s.get("model", "?")
        created = s.get("created_at", "")[:19].replace("T", " ") + " UTC"
        cards.append(
            f'<div class="session-card">'
            f'<div class="session-id"><a href="/{_esc(sid)}">{_esc(sid)}</a></div>'
            f'<div class="session-meta">'
            f"model: <strong>{_esc(model)}</strong> &nbsp;·&nbsp; {_esc(created)}"
            f"</div>"
            f"</div>"
        )

    body = (
        "<h1>claw sessions</h1>"
        "<h2>all saved sessions</h2>"
        f'<div class="session-list">{"".join(cards)}</div>'
    )
    return _html("sessions", body)


def render_session(ls: LoadedSession) -> str:
    meta = ls.meta
    model = meta.get("model", "?")
    created = meta.get("created_at", "")[:19].replace("T", " ") + " UTC"

    # Cumulative token totals
    total_in = sum(t.get("input_tokens", 0) for t in ls.turns)
    total_out = sum(t.get("output_tokens", 0) for t in ls.turns)

    nav = (
        f'<div class="nav">'
        f'<a href="/">← all sessions</a>'
        f'<a href="/api/{_esc(ls.session_id)}">raw JSON</a>'
        f"</div>"
    )

    header = (
        f'<div class="session-header">'
        f"<strong>Session:</strong> {_esc(ls.session_id)}<br>"
        f'<span style="color:#8b949e;font-size:.78rem">'
        f"model: {_esc(model)} &nbsp;·&nbsp; created: {_esc(created)}"
        f" &nbsp;·&nbsp; {len(ls.turns)} turn(s)"
        f" &nbsp;·&nbsp; "
        f'<span class="badge badge-in">{total_in} in</span>'
        f' <span class="badge badge-out">{total_out} out</span>'
        f"</span>"
        f"</div>"
    )

    turns_html = []
    for i, turn in enumerate(ls.turns):
        seq = turn.get("seq", "?")
        ts = turn.get("timestamp", "")[:19].replace("T", " ") + " UTC"
        tin = turn.get("input_tokens", 0)
        tout = turn.get("output_tokens", 0)
        tool_calls = turn.get("tool_calls", [])

        # Build a one-line preview: first user text in this turn
        preview = ""
        for msg in turn.get("messages", []):
            if msg.get("role") == "user":
                for blk in msg.get("content", []):
                    if blk.get("type") == "text" and blk.get("text", "").strip():
                        preview = blk["text"].strip().replace("\n", " ")[:80]
                        break
            if preview:
                break

        strip = _render_tool_strip(tool_calls)
        msgs_html = "".join(_render_message(m) for m in turn.get("messages", []))

        # First turn open by default, rest collapsed
        open_attr = " open" if i == 0 else ""

        summary = (
            f"<summary>"
            f'<span class="turn-chevron">▶</span>'
            f'<span class="turn-seq">Turn {seq}</span>'
            f'<span class="turn-ts">{ts}</span>'
            f'<span class="badge badge-in">{tin} in</span>'
            f'<span class="badge badge-out">{tout} out</span>'
            f'<span class="turn-preview">{_esc(preview)}</span>'
            f"</summary>"
        )

        turns_html.append(
            f'<div class="turn">'
            f'<details class="turn-details"{open_attr}>'
            f"{summary}"
            f'<div class="turn-body">{strip}{msgs_html}</div>'
            f"</details>"
            f"</div>"
        )

    expand_controls = (
        '<div class="expand-controls">'
        "<button onclick=\"document.querySelectorAll('details.turn-details').forEach(d=>d.open=true)\">"
        "Expand all</button>"
        "<button onclick=\"document.querySelectorAll('details.turn-details').forEach(d=>d.open=false)\">"
        "Collapse all</button>"
        "</div>"
    )

    body = (
        nav + "<h1>Session detail</h1>" + header + expand_controls + "".join(turns_html)
    )
    return _html(f"session {ls.session_id[:8]}", body)


# ── HTTP server ────────────────────────────────────────────────────────────────


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        # Print a compact request log instead of the noisy default.
        print(f"  {self.command} {self.path}")

    def _send(self, code: int, content_type: str, body: str | bytes) -> None:
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/") or "/"

        if path == "/":
            self._send(
                200, "text/html; charset=utf-8", render_session_list(Session.list_all())
            )
            return

        if path.startswith("/api/"):
            sid = path[5:]
            try:
                ls = Session.load(sid)
                self._send(
                    200,
                    "application/json",
                    json.dumps(ls.records, indent=2, ensure_ascii=False),
                )
            except FileNotFoundError:
                self._send(404, "text/plain", b"session not found")
            return

        sid = path.lstrip("/")
        try:
            ls = Session.load(sid)
            self._send(200, "text/html; charset=utf-8", render_session(ls))
        except FileNotFoundError:
            self._send(404, "text/plain", b"session not found")


def serve(port: int = 7070) -> None:
    server = HTTPServer(("127.0.0.1", port), _Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"claw viewer  →  {url}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


# ── CLI entry point ────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect saved claw session files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python -m claw_code_python.viewer\n"
            "  python -m claw_code_python.viewer <session-id>\n"
            "  python -m claw_code_python.viewer --serve\n"
            "  python -m claw_code_python.viewer --serve --port 8080\n"
        ),
    )
    parser.add_argument(
        "session_id", nargs="?", help="Session ID to inspect (CLI mode)"
    )
    parser.add_argument("--serve", action="store_true", help="Start HTTP viewer server")
    parser.add_argument("--port", type=int, default=7070, metavar="N")
    args = parser.parse_args()

    if args.serve:
        serve(args.port)
        return

    if args.session_id:
        try:
            ls = Session.load(args.session_id)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            raise SystemExit(1) from e

        print(f"Session: {ls.session_id}")
        print(f"Model:   {ls.meta.get('model', '?')}")
        print(f"Created: {ls.meta.get('created_at', '')[:19]} UTC")
        print(f"Turns:   {len(ls.turns)}")
        print()

        for turn in ls.turns:
            seq = turn.get("seq", "?")
            ts = turn.get("timestamp", "")[:19].replace("T", " ")
            tin, tout = turn.get("input_tokens", 0), turn.get("output_tokens", 0)
            print(f"── Turn {seq}  {ts}  [{tin} in / {tout} out] ──")
            for msg in turn.get("messages", []):
                role = msg.get("role", "?")
                for block in msg.get("content", []):
                    bt = block.get("type")
                    if bt == "text":
                        snippet = block["text"][:120].replace("\n", " ")
                        print(f"  [{role}] {snippet}")
                    elif bt == "tool_use":
                        inp_short = json.dumps(block.get("input", {}))[:80]
                        print(f"  [tool_use] {block['name']}  {inp_short}")
                    elif bt == "tool_result":
                        status = "ERROR" if block.get("is_error") else "ok"
                        content = str(block.get("content", ""))[:100].replace("\n", " ")
                        print(f"  [tool_result] {status}: {content}")
            print()
        return

    # No args -- list all sessions
    sessions = Session.list_all()
    if not sessions:
        print("No sessions found in ~/.claw/sessions/")
        return
    print(f"{'SESSION ID':<40}  {'MODEL':<20}  CREATED")
    print("-" * 80)
    for s in sessions:
        sid = s.get("session_id", "?")
        model = s.get("model", "?")
        created = s.get("created_at", "")[:19].replace("T", " ")
        print(f"{sid:<40}  {model:<20}  {created}")


if __name__ == "__main__":
    main()

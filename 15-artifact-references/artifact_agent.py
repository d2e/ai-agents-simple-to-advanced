"""
Artifact references: when a tool's result is large, don't inline the
whole thing into the conversation - store it once, hand the model back
a short reference (an ID + preview), and give it a second tool to pull
specific slices on demand.

06-context-compaction shrinks old *conversation turns* once history
gets long. This is a different problem: a single tool call (e.g.
searching a big log file) can return something huge on its own. If we
paste all of it into `messages`, every future request resends it -
even if the model only ever needed three lines out of it. Instead we
keep the full content out of the conversation entirely, in an
in-memory store, and let the model ask for exactly the part it needs.
"""

import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"

# The "artifact store" - anything large a tool produces lives here,
# keyed by an id, instead of ever being pasted into `messages` directly.
ARTIFACTS = {}


def _make_fake_logs():
    lines = []
    for i in range(60):
        minute = i
        if i == 37:
            lines.append(f"2026-09-14 10:{minute:02d}:00 ERROR database connection timeout after 30s")
        elif i == 38:
            lines.append(f"2026-09-14 10:{minute:02d}:00 INFO retrying connection to db-primary.internal")
        else:
            lines.append(f"2026-09-14 10:{minute:02d}:00 INFO heartbeat ok")
    return lines


LOG_LINES = _make_fake_logs()

# The full log lives in the artifact store exactly once - search_logs
# only ever returns *which lines matched*, never the log itself, so
# read_artifact can pull a slice around any match (surrounding context
# included) without the whole log ever touching `messages`.
ARTIFACTS["full-log"] = LOG_LINES


def search_logs(query):
    matching_indices = [i for i, line in enumerate(LOG_LINES) if query.lower() in line.lower()]
    preview = "\n".join(f"line {i}: {LOG_LINES[i]}" for i in matching_indices[:3])

    # Spell out the exact call to make - small local models don't
    # reliably compute "3 lines before index 37" on their own, even
    # when given the raw index. Explicit beats implicit here.
    suggestion = None
    if matching_indices:
        first = matching_indices[0]
        start = max(0, first - 3)
        suggestion = f"read_artifact(artifact_id='full-log', start={start}, count=8)"

    return json.dumps({
        "artifact_id": "full-log",
        "total_matches": len(matching_indices),
        "matching_lines": matching_indices,
        "preview": preview,
        "note": f"to see context around the first match, call: {suggestion}",
    })


def read_artifact(artifact_id, start=0, count=5):
    lines = ARTIFACTS.get(artifact_id)
    if lines is None:
        return f"error: unknown artifact_id '{artifact_id}'"
    start = int(start)
    count = int(count)
    return "\n".join(lines[start:start + count]) or "(no more lines)"


TOOLS = {"search_logs": search_logs, "read_artifact": read_artifact}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_logs",
            "description": (
                "Search the server logs for lines containing a query. Returns a "
                "small preview and an artifact_id - use read_artifact to see more."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_artifact",
            "description": "Read a slice of lines from a previously returned artifact_id",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string"},
                    "start": {"type": "integer", "description": "line index to start at, default 0"},
                    "count": {"type": "integer", "description": "how many lines to read, default 5"},
                },
                "required": ["artifact_id"],
            },
        },
    },
]


def call_llm(messages):
    payload = {"model": MODEL, "messages": messages, "tools": TOOL_SCHEMAS, "stream": False}
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, method="POST")
    req.add_header("content-type", "application/json")

    if DEBUG:
        print("\n--- REQUEST ---")
        print(json.dumps(payload, indent=2))

    with urllib.request.urlopen(req) as resp:
        raw = resp.read()

    if DEBUG:
        print("--- RESPONSE ---")
        print(json.dumps(json.loads(raw), indent=2))
        print("--- END ---\n")

    message = json.loads(raw)["message"]
    thinking = message.get("thinking")
    if thinking:
        print(f"[thinking] {thinking}")
    return message


def run_agent(question, max_steps=6):
    messages = [{"role": "user", "content": question}]

    for _ in range(max_steps):
        message = call_llm(messages)
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            print(f"[agent] {message['content']}")
            return message["content"]

        messages.append(message)
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            result = TOOLS[name](**args) if name in TOOLS else f"error: unknown tool '{name}'"
            print(f"[tool:{name}] {result}")
            messages.append({"role": "tool", "content": str(result)})

        # This is the whole point: even though LOG_LINES has 60 entries,
        # `messages` only ever contains what search_logs/read_artifact
        # explicitly returned - previews and requested slices, never
        # the full 60-line log dumped in one go.
        if DEBUG:
            total_chars = sum(len(str(m.get("content", ""))) for m in messages)
            print(f"[context size] {total_chars} chars in `messages` so far "
                  f"(full log is {sum(len(l) for l in LOG_LINES)} chars)")

    return "agent gave up after too many steps"


if __name__ == "__main__":
    question = input(
        "Ask about the logs (e.g. 'search the logs for ERROR and tell me what happened around it'): "
    )
    print("\nFinal answer:", run_agent(question))

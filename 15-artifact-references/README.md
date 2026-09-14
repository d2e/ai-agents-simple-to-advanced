# 15 - Artifact References

`06-context-compaction` shrinks old *conversation turns* once history
gets long. This is a different problem: a single tool call can return
something huge on its own (a big log search, a large file). Pasting
all of it into `messages` means every future request resends it — even
if the model only needed three lines out of it.

Instead, `search_logs()` stores the full log in an in-memory
`ARTIFACTS` store and returns the model a short reference: an
`artifact_id`, a small preview, and which line numbers matched.
`read_artifact()` lets the model pull a specific slice on demand — the
full content only ever enters `messages` in the small pieces actually
requested.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 artifact_agent.py
# try: search the logs for ERROR and tell me what happened around it
DEBUG=1 python3 artifact_agent.py   # prints context size vs. full log size each step
```

## Example

```
[tool:search_logs] {"artifact_id": "full-log", "total_matches": 1, "matching_lines": [37],
 "preview": "line 37: ... ERROR database connection timeout after 30s",
 "note": "to see context around the first match, call: read_artifact(artifact_id='full-log', start=34, count=8)"}
[context size] 332 chars in `messages` so far (full log is 2276 chars)

[tool:read_artifact] ...8 lines including the error and the retry that followed...
[context size] 691 chars in `messages` so far (full log is 2276 chars)

[agent] ...correctly explains the timeout AND the recovery retry...
```

The full 60-line log (2276 chars) never entered `messages` — only a
preview, then one targeted 8-line slice (691 chars total) — yet the
final answer captured both the error and its recovery.

## What's actually happening

- `ARTIFACTS["full-log"]` holds the real data exactly once; nothing in
  `messages` ever duplicates it.
- `search_logs()` returns *which lines matched*, not the lines
  themselves — a pointer, not a payload.
- The `note` field spells out the exact `read_artifact(...)` call to
  make (`start=34, count=8`), rather than leaving the model to compute
  an offset itself — a small local model won't reliably do "3 lines
  before index 37" on its own; being explicit here removed that
  uncertainty entirely.

# 12 - Intent Routing

Classify the request first, then dispatch to a dedicated handler —
instead of giving one agent every tool and letting it decide, like
`04-multi-agent` does via native tool-calling.

The difference from `04-multi-agent`: there, one orchestrator call
decides *and* extracts arguments *and* delegates, all through
tool-calling. Here, classification is a separate, cheaper first step —
it doesn't need tool-calling support at all, and each route only gets
the tools it actually needs. A "chitchat" request never even sees that
`calculator` or `send_email` exist.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 routing_agent.py
# try: what is 45 * 3?
# try: what time is it?
# try: tell me a fun fact about octopuses
```

## Example

```
Ask something: what is 45 * 3?
[router] intent = math
Answer: 45 x 3 = 135

Ask something: what time is it?
[router] intent = time
Answer: The current date and time is 2026-09-14 17:13:15.
```

Notice the "time" route doesn't even call the model to decide what to
do — once intent is known, some routes are simple enough to skip the
LLM for the actual work entirely.

## What's actually happening

- `classify_intent()` is a single, narrow prompt — the only valid
  outputs are the fixed labels, nothing else.
- An unrecognized label falls back to `"chitchat"` — the route with
  the least capability, not the most, so a routing mistake fails safe.
- Each handler (`handle_math`, `handle_time`, `handle_chitchat`) is
  isolated: only `handle_math` ever sees the calculator tool schema.

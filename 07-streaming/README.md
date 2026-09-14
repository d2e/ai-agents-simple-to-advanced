# 07 - Streaming

Every earlier example sets `stream: false` and waits for one full JSON
response. Here we set `stream: true` — Ollama sends back a series of
small JSON objects, one per line, each carrying a tiny piece of the
reply. We print each piece as it arrives instead of waiting for the
whole thing.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 streaming_agent.py
# try: write a 3 line poem about the ocean
DEBUG=1 python3 streaming_agent.py   # print each raw chunk as it arrives
```

## What's actually happening

- With `stream: true`, the HTTP response body is many JSON objects
  separated by newlines, not one — `for line in resp` reads them as
  they land, not all at once.
- Each chunk carries `message.content` (a few characters, sometimes
  one token), plus `"done": false` until the final chunk sets it `true`.
- `print(piece, end="", flush=True)` is what actually makes it feel
  live — without `flush=True`, Python buffers output and it'd all
  appear at once anyway, defeating the point.

## Why it matters

For a single short answer, streaming vs. waiting barely matters. It
matters once replies get long (or a request takes several seconds) —
the user sees progress immediately instead of staring at a blank
screen. It's a UX choice, not a capability change: the model still
generates one token at a time either way, `stream: false` just buffers
those tokens before Ollama gives you the full reply back.

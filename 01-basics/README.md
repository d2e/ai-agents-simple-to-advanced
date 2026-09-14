# 01 - Basics: The Agent Loop

An agent is just: **think → act → observe**, repeat until there's a
final answer. `simple_agent.py` implements it with zero dependencies —
tools are plain functions, the model is called over raw HTTP.

The "protocol" is two plain-text lines: `TOOL: name input` or
`ANSWER: text`. No JSON schema, just string parsing.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.
Defaults to `gemma4:latest`.

## Run

```bash
python3 simple_agent.py
# try: what is 12 * 7, then tell me the time
DEBUG=1 python3 simple_agent.py   # see raw request/response each step
```

## Example

```
Ask something: what is 12 * 7, then tell me the time
[agent] TOOL: calculator 12 * 7
[tool:calculator] 84
[agent] TOOL: get_time
[tool:get_time] 2026-09-14 16:00:19
[agent] ANSWER: 84, and the time is 2026-09-14 16:00:19
```

## Gotcha

Local models don't always stick to "one line only" — they sometimes
cram both a `TOOL:` and `ANSWER:` line into one reply. The loop only
parses the *first* line for exactly this reason; see `run_agent()`.

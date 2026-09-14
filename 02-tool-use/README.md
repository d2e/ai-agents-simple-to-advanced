# 02 - Tool Use: Structured (JSON) Tool Calls

`01-basics` parsed a hand-rolled text line (`TOOL: name input`), which
broke if the model added extra lines. This example uses Ollama's native
tool-calling instead: each tool is a JSON Schema, and the model returns
a structured `tool_calls` field with already-parsed, named arguments —
no text parsing at all. It also lets one tool take several named params
(`convert_temperature(value, from_unit, to_unit)`), and the model can
request multiple tool calls in a single reply.

Still zero dependencies — same `urllib`/`json` as `01-basics`, just a
structured protocol instead of plain text.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.
Defaults to `gemma4:latest` — same model as `01-basics`, better protocol.

## Run

```bash
python3 tool_use_agent.py
# try: convert 100 fahrenheit to celsius, then tell me the time
DEBUG=1 python3 tool_use_agent.py   # see the tools schema + tool_calls JSON
```

## Example

```
Ask something: convert 100 fahrenheit to celsius, then tell me the time
[agent] TOOL: convert_temperature({'from_unit': 'fahrenheit', 'to_unit': 'celsius', 'value': 100})
[tool:convert_temperature] 37.78 celsius
[agent] TOOL: get_time({})
[tool:get_time] 2026-09-14 16:08:10
[agent] 100°F is 37.78°C. The current time is 2026-09-14 16:08:10.
```

Both tool calls came from a single model reply — no round-trip needed
between them.

## What changed vs. 01-basics

- Tool args arrive as a real dict (`call["function"]["arguments"]`) —
  called with `TOOLS[name](**args)`, no string splitting.
- `tools` in the request *is* the model's picture of what it can do —
  good descriptions here directly improve tool selection.
- `tool_calls` is a list, so one reply can trigger several tools.

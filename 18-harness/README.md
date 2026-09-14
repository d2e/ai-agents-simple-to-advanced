# 18 - Harness

Every tutorial since `01-basics` has quietly been its own bespoke
harness — a loop, a tool registry, and whatever plugins (memory,
approval gates) that particular tutorial needed baked directly into
the script. `harness.py` pulls that pattern out into one small
`Harness` class where tools, memory, and an approval gate are
swappable parts you pass in, instead of code you rewrite each time.

This is also, underneath its own API, basically what a framework
(LangChain, CrewAI, ...) *is*. Building one by hand here is what makes
it obvious what a framework is actually buying you in `19-frameworks`.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 harness.py
```

This runs the exact same `Harness.run()` loop three times with
different configuration, demonstrating each plugin in isolation.

## Example

```
=== plain harness: no approval gate, fresh memory each run ===
[tool:calculator] 84
answer: 12 * 7 is 84.

=== guarded harness: same loop, send_email now needs approval ===
[approval] run send_email(...)? [y/N]: n
[denied] send_email
answer: I'm sorry, I was denied permission to send that email.

=== persistent harness: same loop, memory reused across two .run() calls ===
answer: Your favorite color is teal.
```

Same `run()` method, same loop, three completely different behaviors —
driven entirely by what's passed into `__init__`.

## What's actually happening

- `Harness.__init__` takes `tools`, `tool_schemas`, `memory`, and
  `approval_gate` as plain arguments — nothing about the loop itself
  knows or cares what specific tools or policy it's running with.
- Passing the *same* `memory` list into two `.run()` calls is what
  makes state persist (`03-memory`'s whole trick) — the harness has no
  special "remember across calls" code, it just doesn't own the list.
- `approval_gate` is just a set of tool names (`09-human-in-the-loop`'s
  gate) — checked once, generically, instead of hardcoded per tool.
- This is intentionally not feature-complete (no retries, no
  compaction, no RAG) — the point is the *shape*: a loop plus
  pluggable parts, which is the shape every agent framework builds on
  top of.

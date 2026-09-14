# 04 - Multi-Agent: Delegation

In `02-tool-use`, a tool was a one-shot function — call it, get a
string back. Here, some of the top-level agent's "tools" are
**specialists**: each one runs its own complete agent loop (its own
system prompt, its own tool, its own think/act/observe steps) before
handing back a final answer. The **orchestrator** never sees how a
specialist got its answer, only the result — same as delegating to a
coworker instead of watching them work.

`run_agent_loop()` is the same loop used for the orchestrator *and*
both specialists — an agent and a tool look identical from the
outside, whether the tool is one line of code or a whole other agent.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.
Defaults to `gemma4:latest`.

## Run

```bash
python3 multi_agent.py
# try: what is 12 * 7 and what time is it?
DEBUG=1 python3 multi_agent.py
```

## Example

```
Ask something: what is 12 * 7 and what time is it?
[math-agent:calculator] 84
[math-agent] 12 multiplied by 7 is 84.
[orchestrator:ask_math_agent] 12 multiplied by 7 is 84.
[time-agent:get_time] 2026-09-14 16:25:39
[time-agent] It is 4:25 PM on September 14, 2026.
[orchestrator:ask_time_agent] It is 4:25 PM on September 14, 2026.
[orchestrator] 12 multiplied by 7 is 84.

As for the time, it is 4:25 PM on September 14, 2026.
```

The orchestrator split one question into two delegated calls, each
handled by a specialist with a narrower job and its own tool.

## What changed vs. 02-tool-use

- A specialist's "tool implementation" (`ask_math_agent`,
  `ask_time_agent`) is a function that itself calls `run_agent_loop()`
  — it can think and use a tool, not just return a fixed computation.
- The orchestrator's system prompt only describes *when to delegate*,
  not how to solve anything itself — routing is its whole job.

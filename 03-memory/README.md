# 03 - Memory: State Across Turns

`01-basics`/`02-tool-use` forget everything once `run_agent()` returns —
each question starts a fresh `messages` list. Here the agent runs as a
REPL: `messages` stays alive for the whole chat, and gets saved to
`memory.json` after every turn — so it survives quitting and
restarting the script too.

Memory here isn't a special feature, just persistence: save the
message list, load it back before the next turn.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.
Defaults to `gemma4:latest`.

## Run

```bash
python3 memory_agent.py
# tell it something, then type "exit"
python3 memory_agent.py   # run it again — it remembers
```

Commands: `forget` clears memory, `exit` quits.

## Example (two separate runs of the script)

```
$ python3 memory_agent.py
you: my favorite number is 42
[agent] That's a classic! 42 is certainly a memorable number.
you: exit

$ python3 memory_agent.py
(resumed session - 2 messages loaded from memory.json)
you: what is my favorite number?
[agent] You previously told me that your favorite number is 42!
```

## Note

`memory.json` is just the raw `messages` array — open it to see exactly
what the model can and can't "remember" (it's every message, verbatim,
nothing summarized). Real systems usually trim or summarize old
messages once the history gets long, since it all gets resent to the
model on every turn.

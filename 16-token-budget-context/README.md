# 16 - Token-Budget Context Assembly

`06-context-compaction` triggered on "more than N messages" and
summarized whatever didn't fit. Message *count* is a poor proxy for
size, though — one message might be five words, another a huge pasted
log. Here, the full conversation is kept in memory (like
`03-memory`), but every request only sends a *window* of the most
recent messages that fits under a token budget — walking backwards
from the newest message. Anything older than the budget allows is
simply left out, not summarized.

`TOKEN_BUDGET = 60` is deliberately tiny, and `estimate_tokens()` is a
rough `len(text) // 4` heuristic (no tokenizer library) — good enough
to make a budgeting decision, not a real token count.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 budget_agent.py
```

## What I found testing this

```
you: my favorite color is teal
[context] sending 1/1 messages (~6/60 tokens, 0 older messages left out)
[agent] Teal is such a gorgeous color! ...(long, chatty reply)...

you: what is 2+2
[context] sending 1/3 messages (~2/60 tokens, 2 older messages left out)
[agent] 4

you: what is my favorite color?
[context] sending 7/9 messages (~27/60 tokens, 2 older messages left out)
[agent] I don't know your favorite color! You'll have to tell me.
```

The fact was gone after just *one* turn — not because the budget was
absurdly small, but because the model's own verbose reply about teal
alone nearly filled it. The very next question already couldn't afford
to include that exchange.

## The actual lesson

This is the real tradeoff `06-context-compaction` avoids by
summarizing instead of dropping: a pure token-budget window is simple
and cheap (no extra model call to summarize), but anything that falls
outside the window is genuinely gone, not condensed. Verbose replies
eat the budget fast, silently pushing out exactly the earlier context
that made the reply verbose in the first place. In practice, the two
techniques compose: keep a small budgeted window of *recent* messages
verbatim, and compact/summarize whatever falls out of it instead of
discarding it outright.

# 06 - Context Compaction

`03-memory` kept the entire conversation forever — fine for a short
chat, but every message list only grows, and each turn resends (and
pays for) the whole thing. Here, once history passes a threshold, the
older messages get summarized into one short paragraph and replaced by
it — the agent keeps "the gist," not the exact words.

`MAX_MESSAGES = 6` is deliberately tiny so you can see compaction
trigger within a few turns. A real system sizes this against the
model's actual context window (e.g. compact at ~80% full).

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 compaction_agent.py
```

Have a few turns (more than 6 messages) and watch for a
`[compaction] ...` line.

## Example

```
you: my name is Dhiraj and I live in Bangalore
[agent] Hello Dhiraj! ...
you: what is 2+2
[agent] 2 + 2 equals 4.
you: what color is the sky
[agent] Generally blue...
[compaction] 6 old messages -> summary: Dhiraj, who resides in Bangalore,
asked what 2+2 equals (4) and what color the sky is (blue, with variations).
you: remind me my name again
[agent] Your name is Dhiraj.
```

The last answer came entirely from the summary — the original
messages were gone by that point.

## What's actually happening

- `summarize(messages)` just asks the model to compress a transcript
  into 2-3 sentences, explicitly telling it to keep names/numbers/facts.
- `compact_if_needed()` swaps everything except the last `KEEP_RECENT`
  messages for a single `{"role": "system", "content": summary}` message.
- This trades exactness for size: fine details ("2+2 = 4" specifically)
  can blur into paraphrase, but names and key facts usually survive
  because the summarization prompt is told to prioritize them.

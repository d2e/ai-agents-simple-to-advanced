# 20 - Self-Improvement

Every earlier tutorial had a system prompt *you* wrote, and the agent
was stuck with it. Here the agent fails a task, diagnoses why, proposes
a rule to avoid that failure, and keeps the rule only if it measurably
helps. Rules persist to disk, so each run starts smarter than the last.

Nothing is trained — the weights never change. "Learning" is entirely
in-context: a growing set of rules prepended to the prompt. `03-memory`
remembered *facts across turns*; this remembers *corrections across
runs*.

## The four steps

1. **Attempt** — answer the task with the rules learned so far.
2. **Reward** — `word.count(char)` gives ground truth, so the score is
   exact-match, 1 or 0. No LLM judge, nothing to argue with.
3. **Reflect** — show the model its own failures, ask for the root cause
   and one general rule that prevents the whole class.
4. **Keep or discard** — test the candidate on a held-out validation
   set and adopt it *only* if accuracy actually goes up.

Step 4 is the one that's easy to skip and shouldn't be. A model asked
for a rule will always produce one that sounds reasonable; that is not
evidence it works. Without the gate the agent accumulates confident
junk that clutters the prompt and makes things worse.

## Why letter counting

The task is "how many `r`s in `strawberry`". It's a toy, chosen because
it isolates the mechanism:

- The model reliably fails it (tokenization — it sees tokens, not
  letters), so there's headroom to improve.
- Ground truth is one line of Python, so the reward needs no judge.
- **Every failure has the same root cause**, so one rule transfers to
  words the agent has never seen.

That last property is the real precondition, and it's what makes or
breaks this pattern. Tried on GSM8K first, it goes nowhere: the model is
already good at it, and the handful of problems it misses each fail for
their own unrelated reason — so there's no single rule to learn. If your
failures don't share a cause, no amount of reflection will generalize.

Train, validation, and test words are disjoint. The headline number is
measured on test words that never appear during training, so it shows
generalization rather than memorization.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 self_improving_agent.py     # run again to keep improving
rm learned_rules.json               # reset to a blank slate
```

Takes roughly ten minutes — it's ~85 local model calls.

## Example

```
loaded 0 learned rule(s) from previous runs

TEST accuracy before this run: 80%

validation baseline with 0 rule(s): 50%

--- round 1 ---
  train: 75% (2 failed)
    MISS 'l' in parallelogram: 2 != 3
    MISS 's' in possession: 2 != 4
  candidate 1: 100% | For every character count, first visually trace the letters sequentially with a finger or cursor, marking each instance as you count it to prevent overlooking or double-counting.
  candidate 2: 67% | When counting characters in a specific letter within a word, first physically trace the path of the target letter through the word, marking each occurrence with a distinct count tally mark before moving to the next letter segment.
  candidate 3: 67% | When counting a specific letter, mentally highlight each instance of that letter sequentially, and then count the number of highlights to determine the total.
  -> KEEP (50% -> 100%)

--- round 2 ---
  train: 88% (1 failed)
    MISS 's' in mississippi: 3 != 4
  candidate 1: 100% | Before commencing the count, mentally segment the entire word into individual letter slots, and then systematically process the word one slot at a time...
  candidate 2: 100% | After counting the first instance of the target letter, physically draw a non-overlapping, small bounding box around that character...
  candidate 3: 83% | After confirming the starting position before any count, sequentially draw a bounding box around the first instance of the target letter...
  -> DISCARD all (none beat 100%)

============================================================
TEST accuracy: 80% -> 100%  (held-out words, never trained on)
rules learned: 1
```

Three things worth reading off that output:

- The three candidates in round 1 all say roughly the same thing in
  English, and they measure **100% / 67% / 67%**. Phrasing that sounds
  equivalent to you is not equivalent to the model — which is exactly
  why candidates get measured instead of trusted.
- The adopted rule took validation from 50% to 100%, and test from 80%
  to 100% on words it never trained on. The rule generalized.
- Round 2 found two candidates that also scored 100% and discarded both,
  because neither *beat* the bar. The gate stops the prompt growing
  without cause.

## The honest caveat

`gemma4` ships with a "thinking" mode that is **on by default**, and
with it on the model scores 12/12 on these words with no rules at all.
This tutorial sets `THINK = False` to turn it off.

So the agent isn't learning a new capability — it's rediscovering, and
writing down, a reasoning strategy the model already had access to. That
is worth being clear-eyed about: much of what gets called "self-improvement"
in agent systems is this, recovering latent capability through better
prompting, not acquiring anything new. Genuinely new capability needs
weight updates (fine-tuning), which is a different exercise entirely.

The mechanism here is still the real one, and it's the same loop used to
auto-tune production system prompts. Just don't mistake the curve for
the model getting smarter.

## What's actually happening

- `build_prompt()` is the whole improvement — learned rules are just
  text prepended to the system prompt. There is no other state.
- **Answering** runs at `temperature: 0`, so a change in score is the rule
  working rather than sampling luck. **Reflection** deliberately runs at
  `0.8`. At 0 it sees the same failures each round and proposes the
  byte-identical rule every time, making extra rounds pure waste —
  reflection is a search, and search needs variation.
- `reflect()` demands a step-by-step *procedure*, not facts and not a
  restatement of the goal. Asked loosely, the first version of this
  tutorial got back "count every instance, including double letters",
  which measured as no better than nothing and was correctly discarded.
  Rejected candidates are fed back in so the search doesn't revisit its
  own dead ends.
- `validate()` measures each candidate on a held-out set, and an adopted
  rule raises the bar the next one must clear.
- Once validation hits 100% there's no headroom left to prove a new rule
  helps, so later candidates get discarded. That's the gate working, not
  a bug — it's also why a real system needs a harder validation set than
  this one.

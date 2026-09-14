# 10 - Evaluation

Every earlier tutorial was checked by manually reading the output.
That doesn't scale and doesn't catch regressions — if you tweak the
system prompt, swap models, or change a tool, how do you know you
didn't break something that used to work? `eval_agent.py` runs a small
suite of test questions against the agent and checks the final answer
against an expected condition, automatically.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 eval_agent.py
echo $?   # 0 if everything passed, 1 if anything failed - CI-friendly
```

## Example

```
[PASS] 'what is 12 * 7?' -> '12 * 7 is 84.'
[PASS] 'what is 100 / 4?' -> '100 / 4 is 25.'
[PASS] 'what is 9 * 9?' -> '9 * 9 is 81.'
[PASS] 'what is 15 + 27?' -> '15 + 27 is 42.'

4/4 passed
```

## What's actually happening

- Each test case is a question plus a `check(answer) -> bool` function
  — here, just "does the expected number appear in the answer," since
  wording varies but the number shouldn't.
- `contains(expected)` returns a small closure — a factory for check
  functions, so adding a test case is one line, not a new function.
- The script's exit code (`sys.exit`) reflects overall pass/fail, so
  this could gate a CI pipeline the same way a unit test suite would.

This is intentionally the simplest possible eval: exact/substring
matching. Real eval suites often need an LLM to judge whether an
answer is *correct*, not just whether it contains a string — useful
once answers aren't as checkable as a math result.

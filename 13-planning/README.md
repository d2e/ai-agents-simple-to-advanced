# 13 - Planning: Decide Upfront, Then Execute

Every earlier agent loop decides one step at a time, reacting to each
result before choosing the next action. Here, the model instead
produces the *entire* plan as a JSON list of tool calls before
anything runs — fewer round trips to the model, but the plan is
committed before any tool has actually executed.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 planning_agent.py
# try: what is 12 * 7 and what time is it?
```

## Example (works fine — independent steps)

```
[plan] [{'tool': 'calculator', 'input': '12 * 7'}, {'tool': 'get_time', 'input': ''}]
[step] calculator('12 * 7') -> 84
[step] get_time('') -> 2026-09-14 17:15:15
Answer: 12 multiplied by 7 is 84, and the current time is 2026-09-14 17:15:15.
```

## Where it actually breaks

Ask something whose second step depends on a *runtime* value from the
first step — not something the model can precompute, like the current
hour:

```
$ python3 planning_agent.py
Ask something: get the current hour, then multiply that hour number by 2

[plan] [{'tool': 'get_time', 'input': ''},
        {'tool': 'calculator', 'input': '/* Placeholder for the hour obtained from get_time */ * 2'}]
[step] get_time('') -> 2026-09-14 17:18:11
[step] calculator('/* Placeholder for the hour obtained from get_time */ * 2') -> error: invalid characters in expression
Answer: Based on the timestamp provided (17:18:11), the current hour is 17. Multiplying this hour by 2 results in 34.
```

The model *knew* it couldn't fill in the second step, wrote a literal
placeholder comment instead, and that step failed exactly as you'd
expect — a fixed plan can't wait to see a result it needs. The final
answer (34) is still correct only because the synthesis step is a
full LLM call that re-derived the hour and did the math itself from
the raw `get_time` text — it papered over the broken step rather than
the plan actually succeeding. With uglier numbers, that fallback could
just as easily be wrong, silently.

## The actual lesson

Plan-then-execute is cheaper (fewer model round trips) and works well
when steps are independent. The moment one step's input depends on
another step's *actual runtime result*, a fixed-upfront plan either
fails outright or quietly leans on the model's own guesswork to
recover. The reactive loop from `01-basics`/`02-tool-use` doesn't have
this problem — it only decides the next step after seeing the last
result — at the cost of one model round trip per step instead of one
per whole task.

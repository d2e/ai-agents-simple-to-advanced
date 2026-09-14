# 08 - Guardrails: Validate and Retry

We ask the model to extract structured data (name, age, city) as JSON,
then validate the reply against a schema. If it's invalid, we tell the
model exactly what was wrong and ask it to try again — same idea as
the OBSERVATION step in earlier tutorials, just validating structure
instead of running a tool.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 guardrail_agent.py
# try: Jane is in her early thirties and lives in Tokyo
```

## Example

```
Describe someone: Jane is in her early thirties and lives in Tokyo
[attempt 1] ```json
{"name": "Jane", "age": 30, "city": "Tokyo"}
```
[valid] {'name': 'Jane', 'age': 30, 'city': 'Tokyo'}
```

## Two layers, not one

Testing this turned up a real failure mode: models very often wrap
JSON in a ` ```json ... ``` ` code fence even when told to reply with
"ONLY the JSON object" — and a small local model sometimes repeats the
*exact same* fenced reply after being told it's invalid, instead of
fixing it. Retrying alone didn't reliably help.

So there are two layers here, not one:

- `strip_code_fence()` — sanitize the cheap, extremely common failure
  (markdown fences) before even attempting to parse. No retry needed.
- The retry loop — for the rest: missing fields, wrong types, anything
  sanitization can't fix. Each retry tells the model exactly what
  `validate()` found wrong.

Lesson: don't rely purely on "ask the model nicely, then retry" for a
failure you can just fix in code. Retries are for things you can't
predict — schema mismatches, wrong types — not for a formatting quirk
you already know how to normalize.

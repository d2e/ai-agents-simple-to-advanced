# 17 - Transport Resilience

Every earlier tutorial assumed the HTTP call to Ollama just works. It
doesn't always — the server can be down, slow, or briefly overloaded.
`08-guardrails` handled bad *output shape*; this handles the *request
itself* failing.

`call_llm_with_retry()` retries with exponential backoff, but only for
failures a retry can actually fix. A 5xx server error or a connection
failure might succeed on the next try. A 4xx client error (asking for
a model that doesn't exist, a malformed request) will fail identically
every time — retrying it just delays telling the user what's actually
wrong.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 resilient_agent.py
```

This runs three real scenarios against the actual Ollama server — no
simulated/fake failures.

## Example

```
=== 1. normal request (should just succeed) ===
reply: Hello there friend.

=== 2. unknown model - a real 404, non-retryable ===
[resilience] 404 client error - not retrying: {"error":"model 'nonexistent-model-xyz' not found"}
failed immediately, as expected: 404

=== 3. unreachable server - real connection failures, retried then given up ===
[resilience] attempt 1/3: transport error: <urlopen error [Errno 61] Connection refused>
[resilience] retrying in 1s...
[resilience] attempt 2/3: transport error: <urlopen error [Errno 61] Connection refused>
[resilience] retrying in 2s...
[resilience] attempt 3/3: transport error: <urlopen error [Errno 61] Connection refused>
gave up, as expected: gave up after 3 attempts
```

Scenario 2 fails on the *first* attempt, no retries. Scenario 3 waits
1s, then 2s, between attempts (exponential backoff) before giving up.

## What's actually happening

- `urlopen(req, timeout=timeout)` gives every request a real deadline —
  without it, a hung server blocks forever instead of failing so you
  can retry.
- `urllib.error.HTTPError` carries a status code — checking `400 <=
  code < 500` is the entire retryable/non-retryable decision.
- `urllib.error.URLError` / `TimeoutError` cover connection-level
  failures (refused, DNS, timeout) — always worth retrying, since
  there's no "wrong request" to blame.
- Backoff doubles each attempt (`1s, 2s, 4s, ...`) instead of retrying
  immediately — hammering a struggling server at full speed makes
  things worse, not better.

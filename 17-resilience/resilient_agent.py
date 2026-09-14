"""
Transport resilience: every earlier tutorial assumed the HTTP call to
Ollama just works. It doesn't always - the server can be down, slow,
or briefly overloaded. This wraps the same call_llm() from earlier
tutorials with retry-with-backoff, but only for failures a retry can
actually fix.

The key distinction: a 5xx server error or a connection failure might
succeed if you just try again in a second. A 4xx client error (like
asking for a model that doesn't exist) will fail identically every
time - retrying it only wastes time and delays telling the user what's
actually wrong. This script demonstrates both, against the real Ollama
server (no simulated/fake failures).
"""

import json
import time
import urllib.error
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"


def call_llm(messages, model=MODEL, url=API_URL, timeout=5):
    payload = {"model": model, "messages": messages, "stream": False}
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("content-type", "application/json")

    # A real timeout (not just "hope it responds") - without this,
    # a hung server would block forever instead of failing so we can
    # retry.
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()

    return json.loads(raw)["message"]["content"].strip()


def call_llm_with_retry(messages, model=MODEL, url=API_URL, max_attempts=3, base_delay=1):
    for attempt in range(1, max_attempts + 1):
        try:
            return call_llm(messages, model=model, url=url)

        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if 400 <= e.code < 500:
                # Client errors (bad model name, malformed request) are
                # not transient - the exact same request will fail the
                # exact same way every time. Fail fast instead of
                # burning through retries and delaying the real error.
                print(f"[resilience] {e.code} client error - not retrying: {body}")
                raise
            print(f"[resilience] attempt {attempt}/{max_attempts}: server error {e.code}: {body}")

        except (urllib.error.URLError, TimeoutError) as e:
            # Connection refused, DNS failure, timeout - these are
            # exactly the kind of transient problem a retry might fix.
            print(f"[resilience] attempt {attempt}/{max_attempts}: transport error: {e}")

        if attempt < max_attempts:
            delay = base_delay * (2 ** (attempt - 1))  # exponential backoff: 1s, 2s, 4s, ...
            print(f"[resilience] retrying in {delay}s...")
            time.sleep(delay)

    raise RuntimeError(f"gave up after {max_attempts} attempts")


if __name__ == "__main__":
    print("=== 1. normal request (should just succeed) ===")
    try:
        reply = call_llm_with_retry([{"role": "user", "content": "say hi in exactly 3 words"}])
        print(f"reply: {reply}")
    except Exception as e:
        print(f"failed: {e}")

    print("\n=== 2. unknown model - a real 404, non-retryable ===")
    try:
        call_llm_with_retry(
            [{"role": "user", "content": "hi"}],
            model="nonexistent-model-xyz",
        )
    except urllib.error.HTTPError as e:
        print(f"failed immediately, as expected: {e.code}")

    print("\n=== 3. unreachable server - real connection failures, retried then given up ===")
    try:
        call_llm_with_retry(
            [{"role": "user", "content": "hi"}],
            url="http://localhost:11499/api/chat",  # nothing listens here
            max_attempts=3,
            base_delay=1,
        )
    except Exception as e:
        print(f"gave up, as expected: {e}")

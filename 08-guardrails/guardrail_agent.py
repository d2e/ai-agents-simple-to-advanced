"""
Guardrails: validate the model's output, and retry with feedback when
it doesn't match the shape you asked for.

We ask the model to extract structured data (name, age, city) as JSON.
Models don't always follow instructions exactly - a common real
failure is wrapping JSON in a markdown code fence (```json ... ```),
which breaks json.loads() even though a human would read it fine. So
we validate the reply, and if it's invalid, tell the model exactly
what was wrong and ask it to try again - same idea as the OBSERVATION
step in earlier tutorials, just validating structure instead of
running a tool.
"""

import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"

REQUIRED_FIELDS = {"name": str, "age": int, "city": str}


def call_llm(messages):
    payload = {"model": MODEL, "messages": messages, "stream": False}
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, method="POST")
    req.add_header("content-type", "application/json")

    if DEBUG:
        print("\n--- REQUEST ---")
        print(json.dumps(payload, indent=2))

    with urllib.request.urlopen(req) as resp:
        raw = resp.read()

    if DEBUG:
        print("--- RESPONSE ---")
        print(json.dumps(json.loads(raw), indent=2))
        print("--- END ---\n")

    return json.loads(raw)["message"]["content"].strip()


def strip_code_fence(text):
    # Models very commonly wrap JSON in a markdown code fence
    # (```json ... ```) even when told to reply with "ONLY the JSON
    # object" - this is cheap to fix ourselves rather than spend a
    # whole retry asking the model to stop doing it.
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    lines = lines[1:]  # drop the opening ``` or ```json line
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def validate(data):
    """Return an error string describing what's wrong, or None if valid."""
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in data:
            return f"missing field '{field}'"
        if not isinstance(data[field], expected_type):
            got = type(data[field]).__name__
            return f"field '{field}' should be {expected_type.__name__}, got {got}"
    return None


def extract_contact(sentence, max_retries=3):
    messages = [{
        "role": "user",
        "content": (
            "Extract the name, age, and city from this sentence as JSON "
            "with exactly these keys: name (string), age (integer), "
            "city (string). Reply with ONLY the JSON object, no other text.\n\n"
            f"Sentence: {sentence}"
        ),
    }]

    for attempt in range(1, max_retries + 1):
        reply = call_llm(messages)
        print(f"[attempt {attempt}] {reply}")

        try:
            data = json.loads(strip_code_fence(reply))
            error = validate(data)
        except json.JSONDecodeError as e:
            data = None
            error = f"not valid JSON ({e})"

        if error is None:
            print(f"[valid] {data}")
            return data

        print(f"[invalid] {error}")
        # Feed the failure back exactly like a tool OBSERVATION - the
        # model sees what it got wrong and gets a chance to fix it.
        messages.append({"role": "assistant", "content": reply})
        messages.append({
            "role": "user",
            "content": f"That reply was invalid: {error}. Reply again with ONLY the corrected JSON object.",
        })

    print("[guardrail] gave up after max retries")
    return None


if __name__ == "__main__":
    sentence = input(
        "Describe someone (e.g. 'Jane is in her early thirties and lives in Tokyo'): "
    )
    print("\nResult:", extract_contact(sentence))

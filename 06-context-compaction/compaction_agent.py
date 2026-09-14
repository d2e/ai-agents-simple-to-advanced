"""
Context compaction: summarize old messages instead of resending them
forever.

03-memory persisted the entire conversation and resent all of it every
turn - fine for a short chat, but every message list ever grows, and
each turn resends (and pays for) the whole thing. Here, once the
history passes a threshold, we ask the model to summarize the older
messages into one short paragraph and replace them with that summary -
keeping the most recent messages verbatim. The conversation "remembers
the gist" of old turns instead of the exact words.

MAX_MESSAGES is deliberately tiny (6) so you can see compaction trigger
within a few turns. A real system would size this against the model's
actual context window (e.g. compact once you're using ~80% of it).
"""

import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"

MAX_MESSAGES = 6   # trigger compaction once history exceeds this many messages
KEEP_RECENT = 2    # always leave this many of the most recent messages untouched


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

    message = json.loads(raw)["message"]
    thinking = message.get("thinking")
    if thinking:
        print(f"[thinking] {thinking}")
    return message["content"].strip()


def summarize(messages):
    # Ask the model to compress a chunk of past conversation into a
    # few sentences - this is the entire compaction mechanism.
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    prompt = (
        "Summarize the following conversation in 2-3 short sentences, "
        "keeping any names, numbers, or facts the user shared:\n\n"
        f"{transcript}"
    )
    return call_llm([{"role": "user", "content": prompt}])


def compact_if_needed(messages):
    if len(messages) <= MAX_MESSAGES:
        return messages

    older = messages[:-KEEP_RECENT]
    recent = messages[-KEEP_RECENT:]

    summary = summarize(older)
    print(f"[compaction] {len(older)} old messages -> summary: {summary}")

    # Replace the older messages with a single summary message, so the
    # next request is much shorter but still carries the gist forward.
    return [{"role": "system", "content": f"Summary of earlier conversation: {summary}"}] + recent


if __name__ == "__main__":
    messages = []
    print(f"Chat away (history compacts after {MAX_MESSAGES} messages). 'exit' quits.\n")

    while True:
        user_input = input("you: ").strip()
        if not user_input:
            continue
        if user_input == "exit":
            break

        messages.append({"role": "user", "content": user_input})
        reply = call_llm(messages)
        print(f"[agent] {reply}")
        messages.append({"role": "assistant", "content": reply})

        messages = compact_if_needed(messages)

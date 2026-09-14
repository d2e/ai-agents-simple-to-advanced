"""
Token-budget context assembly: pick what to send based on an actual
size budget, not a message count.

06-context-compaction triggered on "more than N messages" and
summarized whatever didn't fit. That works, but message *count* is a
poor proxy for size - one message might be five words, another might
be a huge pasted error log. Here we keep the full conversation in
memory (like 03-memory), but every time we call the model we assemble
a *window* of the most recent messages that fits under a token budget,
walking backwards from the newest message. Anything older than the
budget allows is simply left out of that request, not summarized.
"""

import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"

# Deliberately tiny so a handful of chat turns is enough to exceed it.
# A real system would size this against the model's actual context
# window, minus room for the reply (e.g. 80% of the limit).
TOKEN_BUDGET = 60


def estimate_tokens(text):
    # No tokenizer library - ~4 characters per token is a common rough
    # approximation for English text. Good enough to make budgeting
    # decisions; not accurate enough to rely on for a real token count.
    return max(1, len(text) // 4)


def assemble_context(messages, budget):
    """Return the most recent messages that fit under `budget` tokens,
    walking backwards from the newest message, plus how many tokens
    that window costs and how many older messages got left out."""
    included = []
    total_tokens = 0

    for message in reversed(messages):
        cost = estimate_tokens(message["content"])
        if included and total_tokens + cost > budget:
            break  # always include at least the latest message, even if it alone exceeds budget
        included.append(message)
        total_tokens += cost

    included.reverse()
    dropped = len(messages) - len(included)
    return included, total_tokens, dropped


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


if __name__ == "__main__":
    messages = []  # full history - never trimmed, unlike what we send
    print(f"Chat away (only ~{TOKEN_BUDGET} tokens of history are sent each turn). 'exit' quits.\n")

    while True:
        user_input = input("you: ").strip()
        if not user_input:
            continue
        if user_input == "exit":
            break

        messages.append({"role": "user", "content": user_input})

        window, used_tokens, dropped = assemble_context(messages, TOKEN_BUDGET)
        print(f"[context] sending {len(window)}/{len(messages)} messages "
              f"(~{used_tokens}/{TOKEN_BUDGET} tokens, {dropped} older messages left out)")

        reply = call_llm(window)
        print(f"[agent] {reply}")
        messages.append({"role": "assistant", "content": reply})

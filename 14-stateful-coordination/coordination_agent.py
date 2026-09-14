"""
Stateful coordination: multiple specialists read and write one shared
workspace, instead of each one just handing back a final answer for an
orchestrator to stitch together (04-multi-agent's approach).

In 04-multi-agent, a specialist is a black box: call it, get text
back, that's the only channel. Here, several specialist calls all read
and write the same shared_state dict directly - each one sees exactly
what earlier specialists have already contributed (not a paraphrase of
it), and can use that to avoid duplicating work. This is the
"blackboard" pattern: a shared workspace multiple agents build up over
the course of one task.
"""

import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"


def call_llm(prompt):
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False}
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


def researcher(topic, angle, shared_state):
    """Add a couple of facts about `topic` (from a specific `angle`) to
    the shared workspace. Sees what's already there, so it can avoid
    repeating a fact a previous researcher already contributed."""
    existing = "\n".join(f"- {fact}" for fact in shared_state["facts"]) or "(none yet)"
    prompt = (
        f"Give exactly 2 short, distinct facts about {topic}, focusing on {angle}. "
        f"Do not repeat any of these already-known facts:\n{existing}\n\n"
        "Reply with just the 2 facts, one per line, no numbering."
    )
    reply = call_llm(prompt)
    new_facts = [line.strip("- ").strip() for line in reply.splitlines() if line.strip()]

    # Writing straight into the shared dict - not returning a value for
    # a caller to relay - is what makes this "shared state" rather than
    # 04-multi-agent's "return a final answer."
    shared_state["facts"].extend(new_facts)

    print(f"[researcher:{angle}] added {len(new_facts)} facts")
    for fact in new_facts:
        print(f"    - {fact}")


def writer(topic, shared_state):
    """Read everything in the shared workspace and produce a summary -
    written after every researcher has already contributed."""
    facts = "\n".join(f"- {fact}" for fact in shared_state["facts"])
    prompt = f"Using ONLY these facts about {topic}, write a 2-3 sentence summary:\n\n{facts}"
    return call_llm(prompt)


def run_coordinator(topic, angles):
    shared_state = {"facts": []}

    for angle in angles:
        researcher(topic, angle, shared_state)

    summary = writer(topic, shared_state)
    return summary, shared_state


if __name__ == "__main__":
    topic = input("Research topic (e.g. 'honey bees'): ")
    summary, shared_state = run_coordinator(topic, ["diet", "communication"])
    print("\n[shared_state.facts]")
    for fact in shared_state["facts"]:
        print(f"  - {fact}")
    print("\nSummary:", summary)

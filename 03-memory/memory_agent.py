"""
Memory: giving the agent state across turns.

01-basics and 02-tool-use both forget everything the moment run_agent()
returns - each question starts a fresh `messages` list. Here we keep
`messages` alive for an entire chat session (a REPL loop), and save it
to a JSON file so it survives even quitting and restarting the script.

The whole trick: memory is just "don't throw the conversation away."
Nothing fancier than persisting the same message list 02-tool-use
already builds, then loading it back before the next turn.
"""

import datetime
import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"

# Stored next to this script so it works regardless of your cwd.
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")


# --- tools (same as 02-tool-use, trimmed to keep this example focused) ---

def calculator(expression):
    allowed = set("0123456789+-*/(). ")
    if not all(c in allowed for c in expression):
        return "error: invalid characters in expression"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"


def get_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


TOOLS = {"calculator": calculator, "get_time": get_time}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a basic arithmetic expression, e.g. '2 + 2'",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current date and time",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# --- memory: just reading/writing the message list as JSON ---------------

def load_memory():
    if os.path.isfile(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return []


def save_memory(messages):
    with open(MEMORY_FILE, "w") as f:
        json.dump(messages, f, indent=2)


# --- LLM call (stdlib only, same shape as 02-tool-use) --------------------

def call_llm(messages):
    payload = {"model": MODEL, "messages": messages, "tools": TOOL_SCHEMAS, "stream": False}
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
    return message


# --- one turn of the agent loop, mutating the shared `messages` list -----

def agent_turn(messages, user_input, max_steps=5):
    # Appending straight onto the caller's list (rather than returning a
    # new one) is what makes memory persist across turns - the REPL loop
    # below reuses the same list, and saves it to disk, after every turn.
    messages.append({"role": "user", "content": user_input})

    for _ in range(max_steps):
        message = call_llm(messages)  # THINK
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            print(f"[agent] {message['content']}")
            messages.append(message)
            return

        messages.append(message)
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if name not in TOOLS:
                result = f"error: unknown tool '{name}'"
            else:
                result = TOOLS[name](**args)  # ACT
            print(f"[tool:{name}] {result}")
            messages.append({"role": "tool", "content": str(result)})  # OBSERVE

    print("[agent] gave up after too many steps")


if __name__ == "__main__":
    messages = load_memory()
    if messages:
        print(f"(resumed session - {len(messages)} messages loaded from {MEMORY_FILE})")
    print("Chat away. 'forget' clears memory, 'exit' quits.\n")

    while True:
        user_input = input("you: ").strip()
        if not user_input:
            continue
        if user_input == "exit":
            break
        if user_input == "forget":
            messages = []
            save_memory(messages)
            print("(memory cleared)")
            continue

        agent_turn(messages, user_input)
        save_memory(messages)  # persist after every turn, not just at exit

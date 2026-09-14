"""
Human-in-the-loop: pause and ask a human before running a "risky" tool.

02-tool-use ran every tool call the model asked for automatically.
That's fine for a calculator, but not for something with real
consequences (sending an email, deleting a file, spending money).
Here, tools in RISKY_TOOLS require a y/n confirmation from the human
before they run - if denied, the model is told the action was denied
(not why it succeeded or failed) so it can react sensibly instead of
just trying again blindly.
"""

import datetime
import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"


# --- tools -----------------------------------------------------------------

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


def send_email(to, subject, body):
    # Simulated - a real version would call an email API here. The
    # point of this tutorial is the approval step, not email sending.
    return f"email sent to {to} (subject: {subject!r})"


TOOLS = {
    "calculator": calculator,
    "get_time": get_time,
    "send_email": send_email,
}

# Tools that must be approved by a human before they run. Everything
# else in TOOLS runs automatically, same as 02-tool-use.
RISKY_TOOLS = {"send_email"}

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
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email to someone",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]


# --- LLM call (stdlib only, same shape as 02-tool-use) ----------------------

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


# --- the agent loop, with an approval gate ----------------------------------

def run_agent(user_input, max_steps=5):
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_steps):
        message = call_llm(messages)  # THINK
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            print(f"[agent] {message['content']}")
            return message["content"]

        messages.append(message)
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]

            if name in RISKY_TOOLS:
                answer = input(f"[approval needed] run {name}({args})? [y/N]: ").strip().lower()
                if answer != "y":
                    print(f"[denied] {name}")
                    # Tell the model it was denied - not why - so it can
                    # react (e.g. apologize, ask what to do instead)
                    # instead of silently retrying the same call.
                    messages.append({"role": "tool", "content": "denied by user"})
                    continue

            if name not in TOOLS:
                result = f"error: unknown tool '{name}'"
            else:
                result = TOOLS[name](**args)  # ACT
            print(f"[tool:{name}] {result}")
            messages.append({"role": "tool", "content": str(result)})  # OBSERVE

    return "agent gave up after too many steps"


if __name__ == "__main__":
    question = input(
        "Ask something (e.g. 'email jane@example.com subject Hi body Hello there'): "
    )
    print("\nFinal answer:", run_agent(question))

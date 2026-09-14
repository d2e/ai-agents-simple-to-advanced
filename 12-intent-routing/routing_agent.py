"""
Intent routing: classify the request first, then dispatch to a
dedicated handler - instead of giving one agent every tool and letting
it figure out what to do (04-multi-agent's approach).

Why this is a different pattern from 04-multi-agent: there, a single
orchestrator call decides *and* extracts arguments *and* delegates, all
via native tool-calling. Here, classification is a separate, cheaper
first step - it doesn't need tool-calling support at all, it can use a
smaller/faster model, and each route can be given only the tools (and
system prompt) it actually needs. That narrows what an unexpected
request can do: a "chitchat" request never even sees the calculator or
email tool exist.
"""

import datetime
import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"

INTENTS = ["math", "time", "chitchat"]


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


def call_llm(messages, tools=None):
    payload = {"model": MODEL, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
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

    return json.loads(raw)["message"]


def classify_intent(user_input):
    # A tight, single-purpose prompt: the only valid outputs are the
    # three labels below, nothing else. This step never touches tools.
    prompt = (
        f"Classify the request into exactly one of these labels: {', '.join(INTENTS)}.\n"
        "Reply with ONLY the label, nothing else.\n\n"
        f"Request: {user_input}"
    )
    message = call_llm([{"role": "user", "content": prompt}])
    label = message["content"].strip().lower()
    return label if label in INTENTS else "chitchat"  # unrecognized -> safest route


def handle_math(user_input):
    tool_schema = [{
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a basic arithmetic expression",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    }]
    messages = [{"role": "user", "content": user_input}]

    message = call_llm(messages, tool_schema)
    tool_calls = message.get("tool_calls")
    if not tool_calls:
        return message["content"]

    call = tool_calls[0]
    result = calculator(**call["function"]["arguments"])
    messages.append(message)
    messages.append({"role": "tool", "content": result})
    return call_llm(messages)["content"]


def handle_time(user_input):
    # This route doesn't even need the model to decide - the only
    # thing "time" intent can mean is calling get_time.
    return f"The current date and time is {get_time()}."


def handle_chitchat(user_input):
    return call_llm([{"role": "user", "content": user_input}])["content"]


ROUTES = {
    "math": handle_math,
    "time": handle_time,
    "chitchat": handle_chitchat,
}


def run_agent(user_input):
    intent = classify_intent(user_input)
    print(f"[router] intent = {intent}")
    return ROUTES[intent](user_input)


if __name__ == "__main__":
    question = input("Ask something (math, time, or just chat): ")
    print("\nAnswer:", run_agent(question))

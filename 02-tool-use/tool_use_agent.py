"""
Tool use, upgraded: structured (JSON) tool calls instead of the
plain-text "TOOL: name input" hack from 01-basics.

Why this matters: in 01-basics, the model had to write a single line of
text in an exact format, and we had to parse it ourselves - which broke
the moment the model added an extra line (see 01-basics' README). Here,
we describe each tool as a JSON schema and Ollama's /api/chat handles
getting the model to emit a structured tool call - the arguments arrive
as an already-parsed dict, not a string we have to split apart. It also
lets a tool take multiple *named* parameters (see convert_temperature
below), which the old single-string-blob protocol couldn't express.

Still zero third-party libraries: same urllib/json stdlib approach as
01-basics, just a different (structured) request/response shape.
"""

import datetime
import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"


# --- tools ---------------------------------------------------------------
# Each tool is a plain Python function taking keyword arguments that
# match its JSON schema below (see TOOL_SCHEMAS). No string parsing here
# at all - the model's arguments arrive already typed and named.

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


def convert_temperature(value, from_unit, to_unit):
    # A multi-parameter tool - this is the kind of call the plain-text
    # "TOOL: name <single input>" protocol from 01-basics couldn't
    # express cleanly, but a JSON schema handles without any extra work.

    # Step 1: convert whatever unit we were given into celsius.
    if from_unit == "celsius":
        celsius = value
    elif from_unit == "fahrenheit":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "kelvin":
        celsius = value - 273.15
    else:
        return f"error: unknown unit '{from_unit}'"

    # Step 2: convert from celsius into whatever unit was requested.
    if to_unit == "celsius":
        result = celsius
    elif to_unit == "fahrenheit":
        result = celsius * 9 / 5 + 32
    elif to_unit == "kelvin":
        result = celsius + 273.15
    else:
        return f"error: unknown unit '{to_unit}'"

    return f"{result:.2f} {to_unit}"


# Maps a tool name to the function that actually runs it.
TOOLS = {
    "calculator": calculator,
    "get_time": get_time,
    "convert_temperature": convert_temperature,
}

# The JSON Schema description of each tool - this is what gets sent in
# the "tools" field of the request and is how the model learns what
# tools exist, what they do, and exactly what arguments they need.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a basic arithmetic expression, e.g. '2 + 2'",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "math expression to evaluate"},
                },
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
            "name": "convert_temperature",
            "description": "Convert a temperature value between celsius, fahrenheit, and kelvin",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "the temperature value to convert"},
                    "from_unit": {"type": "string", "enum": ["celsius", "fahrenheit", "kelvin"]},
                    "to_unit": {"type": "string", "enum": ["celsius", "fahrenheit", "kelvin"]},
                },
                "required": ["value", "from_unit", "to_unit"],
            },
        },
    },
]


# --- LLM call (stdlib only) -----------------------------------------------

def call_llm(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOL_SCHEMAS,
        "stream": False,
    }
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

    data = json.loads(raw)
    message = data["message"]

    thinking = message.get("thinking")
    if thinking:
        print(f"[thinking] {thinking}")

    # Return the whole message (not just text) - unlike 01-basics we now
    # need to see the structured "tool_calls" field, not just "content".
    return message


# --- the agent loop --------------------------------------------------------

def run_agent(user_input, max_steps=5):
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_steps):
        message = call_llm(messages)  # THINK
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            # No tool call in the response -> the model is done.
            print(f"[agent] {message['content']}")
            return message["content"]

        # Record the model's own tool-call message before the results,
        # so it has a record of what it asked for on the next turn.
        messages.append(message)

        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]  # already a dict - no parsing needed
            print(f"[agent] TOOL: {name}({args})")

            if name not in TOOLS:
                result = f"error: unknown tool '{name}'"
            else:
                result = TOOLS[name](**args)  # ACT
            print(f"[tool:{name}] {result}")

            # OBSERVE: Ollama expects tool results back as role "tool".
            messages.append({"role": "tool", "content": str(result)})

    return "agent gave up after too many steps"


if __name__ == "__main__":
    question = input(
        "Ask something (e.g. 'convert 100 fahrenheit to celsius, then tell me the time'): "
    )
    print("\nFinal answer:", run_agent(question))

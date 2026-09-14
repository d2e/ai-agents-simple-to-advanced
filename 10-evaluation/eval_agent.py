"""
Evaluation: automated pass/fail checks instead of eyeballing output.

Every earlier tutorial was verified by manually reading what the agent
printed. That doesn't scale, and it doesn't catch regressions - if you
tweak the system prompt, swap models, or change a tool, how do you
know you didn't break something that used to work? Here we define a
small set of test cases (a question + a check on the final answer) and
run them all automatically, printing a pass/fail summary.
"""

import datetime
import json
import os
import sys
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"


# --- the agent under test (same shape as 02-tool-use) -----------------------

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

    return json.loads(raw)["message"]


def run_agent(question, max_steps=5):
    messages = [{"role": "user", "content": question}]
    for _ in range(max_steps):
        message = call_llm(messages)
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            return message["content"]

        messages.append(message)
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if name not in TOOLS:
                result = f"error: unknown tool '{name}'"
            else:
                result = TOOLS[name](**args)
            messages.append({"role": "tool", "content": str(result)})

    return "(agent gave up after too many steps)"


# --- the eval suite ----------------------------------------------------------

def contains(expected):
    """Build a check function that passes if `expected` appears in the answer."""
    def check(answer):
        return expected in answer
    return check


TEST_CASES = [
    {"question": "what is 12 * 7?", "check": contains("84")},
    {"question": "what is 100 / 4?", "check": contains("25")},
    {"question": "what is 9 * 9?", "check": contains("81")},
    {"question": "what is 15 + 27?", "check": contains("42")},
]


def run_eval():
    passed = 0
    for case in TEST_CASES:
        answer = run_agent(case["question"])
        ok = case["check"](answer)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['question']!r} -> {answer!r}")
        if ok:
            passed += 1

    total = len(TEST_CASES)
    print(f"\n{passed}/{total} passed")
    return passed == total


if __name__ == "__main__":
    success = run_eval()
    sys.exit(0 if success else 1)

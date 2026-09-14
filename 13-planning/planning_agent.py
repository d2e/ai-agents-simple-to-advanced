"""
Planning: decide the whole sequence of steps upfront, then execute it -
instead of reacting one step at a time like every earlier tutorial's
agent loop (decide, act, observe, decide again).

Plan-then-execute needs far fewer round trips to the model (one call
to plan, one call per tool, one call to synthesize - vs. a reactive
loop's one call per step). The tradeoff: the plan is fixed before any
tool has actually run, so it can't adapt to a result it didn't expect.
See the README for a concrete case where that bites.
"""

import datetime
import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"


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
    # Same fix as 08-guardrails - models often wrap JSON in ```json fences.
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def make_plan(question):
    prompt = (
        "Break this request into an ordered list of tool calls needed to "
        "answer it. Available tools:\n"
        "- calculator(expression)\n"
        "- get_time() - takes no input\n\n"
        "Reply with ONLY a JSON array like:\n"
        '[{"tool": "calculator", "input": "2 + 2"}, {"tool": "get_time", "input": ""}]\n\n'
        f"Request: {question}"
    )
    reply = call_llm([{"role": "user", "content": prompt}])
    return json.loads(strip_code_fence(reply))


def execute_plan(plan):
    results = []
    for step in plan:
        tool = step["tool"]
        tool_input = step.get("input", "")
        if tool not in TOOLS:
            result = f"error: unknown tool '{tool}'"
        elif tool_input:
            result = TOOLS[tool](tool_input)
        else:
            result = TOOLS[tool]()
        print(f"[step] {tool}({tool_input!r}) -> {result}")
        results.append({"tool": tool, "input": tool_input, "result": result})
    return results


def synthesize(question, results):
    context = "\n".join(f"- {r['tool']}({r['input']!r}) = {r['result']}" for r in results)
    prompt = (
        f"Original request: {question}\n\n"
        f"Steps executed and their results:\n{context}\n\n"
        "Using these results, answer the original request in one or two sentences."
    )
    return call_llm([{"role": "user", "content": prompt}])


def run_agent(question):
    plan = make_plan(question)
    print(f"[plan] {plan}")
    results = execute_plan(plan)
    return synthesize(question, results)


if __name__ == "__main__":
    question = input("Ask something (e.g. 'what is 12 * 7 and what time is it?'): ")
    print("\nAnswer:", run_agent(question))

"""
Multi-agent: one agent's "tool" is actually another whole agent.

In 02-tool-use, a tool was just a one-shot Python function (calculator,
get_time) - call it, get a string back, done. Here, some of the
top-level agent's "tools" are specialists: each one runs its own
complete agent loop (its own system prompt, its own tool, its own
THINK/ACT/OBSERVE steps) before handing back a final answer. The
top-level "orchestrator" agent never sees how a specialist got its
answer - only the result, the same way delegating a task to a coworker
doesn't require watching them do it.
"""

import datetime
import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"


# --- plain tools, exactly like 02-tool-use --------------------------------

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


# --- LLM call (stdlib only, same shape as 02-tool-use) --------------------

def call_llm(messages, tools):
    payload = {"model": MODEL, "messages": messages, "tools": tools, "stream": False}
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


# --- a small, reusable agent loop - both specialists and the -------------
# --- orchestrator below are just this function called with different -----
# --- system prompts and tools.                                        ----

def run_agent_loop(label, system_prompt, tool_schemas, tool_impls, question, max_steps=5):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    for _ in range(max_steps):
        message = call_llm(messages, tool_schemas)  # THINK
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            print(f"[{label}] {message['content']}")
            return message["content"]

        messages.append(message)
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if name not in tool_impls:
                result = f"error: unknown tool '{name}'"
            else:
                result = tool_impls[name](**args)  # ACT (may itself be a specialist)
            print(f"[{label}:{name}] {result}")
            messages.append({"role": "tool", "content": str(result)})  # OBSERVE

    return f"({label} gave up after too many steps)"


# --- specialists: each is a full agent loop with one tool -----------------

def ask_math_agent(question):
    return run_agent_loop(
        label="math-agent",
        system_prompt=(
            "You are a math specialist. Use the calculator tool for any "
            "arithmetic, then answer in one short sentence."
        ),
        tool_schemas=[{
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
        }],
        tool_impls={"calculator": calculator},
        question=question,
    )


def ask_time_agent(question):
    return run_agent_loop(
        label="time-agent",
        system_prompt=(
            "You are a clock specialist. Use the get_time tool to answer any "
            "question about the current date or time, then answer in one "
            "short sentence."
        ),
        tool_schemas=[{
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "Get the current date and time",
                "parameters": {"type": "object", "properties": {}},
            },
        }],
        tool_impls={"get_time": get_time},
        question=question,
    )


# --- the orchestrator: its "tools" are the specialists above --------------

SPECIALISTS = {
    "ask_math_agent": ask_math_agent,
    "ask_time_agent": ask_time_agent,
}

ORCHESTRATOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ask_math_agent",
            "description": "Delegate any arithmetic or calculation question to the math specialist",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_time_agent",
            "description": "Delegate any question about the current date or time to the clock specialist",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
]


def run_orchestrator(user_input):
    # The orchestrator is the exact same loop as a specialist - just
    # given specialists as its "tools" instead of plain functions. That
    # symmetry is the point: an agent and a tool look identical from the
    # outside, whether the tool is one line of code or another full agent.
    return run_agent_loop(
        label="orchestrator",
        system_prompt=(
            "You are a coordinator. For math questions, delegate to "
            "ask_math_agent. For date/time questions, delegate to "
            "ask_time_agent. Combine their answers into one final reply."
        ),
        tool_schemas=ORCHESTRATOR_TOOLS,
        tool_impls=SPECIALISTS,
        question=user_input,
    )


if __name__ == "__main__":
    question = input("Ask something (e.g. 'what is 12 * 7 and what time is it?'): ")
    print("\nFinal answer:", run_orchestrator(question))

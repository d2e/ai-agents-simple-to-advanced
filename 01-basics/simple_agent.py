"""
Minimal agent, no third-party libraries.

An "agent" here is just a loop:
  1. THINK  - ask the LLM what to do next
  2. ACT    - if it asked for a tool, run that tool
  3. OBSERVE - feed the tool's result back to the LLM
  4. repeat until the LLM gives a final ANSWER

The LLM is called over plain HTTP with urllib (stdlib), so there's
no SDK dependency. Tools are just plain Python functions.
"""

import datetime
import json
import os
import urllib.request

# Local Gemma model served by Ollama (ollama.com) - no API key needed.
# Swap these two constants to point at a different local model or a
# hosted API instead.
API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"

# Set DEBUG=1 in the environment to print the raw HTTP request/response
# sent to the model on every step (useful for seeing exactly what the
# agent loop is doing under the hood).
DEBUG = os.environ.get("DEBUG") == "1"


# --- tools -------------------------------------------------------------
# Tools are just plain Python functions that take a string input and
# return a string result. The agent loop calls these by name whenever
# the model asks for a tool - there's no special "tool" type or schema.

def calculator(expr):
    # Only allow characters needed for basic arithmetic before calling
    # eval(), so the model can't smuggle in arbitrary Python code.
    allowed = set("0123456789+-*/(). ")
    if not all(c in allowed for c in expr):
        return "error: invalid characters in expression"
    try:
        # Empty globals/locals plus the character whitelist above keep
        # this eval() limited to arithmetic - no builtins are reachable.
        return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"


def get_time(_input):
    # This tool ignores its input entirely - it always returns "now".
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# The model only ever sees tool *names* (via the system prompt below),
# so this dict is what maps a name it picks back to real code to run.
TOOLS = {
    "calculator": calculator,
    "get_time": get_time,
}

# This prompt is the entire "protocol" between us and the model: instead
# of a formal tool-calling API, we just tell it to reply with one of two
# plain-text line formats and parse those lines ourselves below.
SYSTEM_PROMPT = """You are a simple agent that can use tools to answer questions.

Available tools:
- calculator: takes a math expression string, e.g. "2 + 2", returns the result
- get_time: takes no input, returns the current date and time

To use a tool, reply with EXACTLY one line:
TOOL: <tool_name> <input>

When you have the final answer, reply with EXACTLY one line:
ANSWER: <your answer>

Never output anything else. One line per reply, no explanations outside that.
"""


# --- LLM call (stdlib only) ---------------------------------------------

def call_llm(messages):
    # Ollama's /api/chat expects the system prompt as just another
    # message in the list, tagged with role "system".
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "stream": False,  # get one full JSON response back, not a stream of chunks
    }
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, method="POST")
    req.add_header("content-type", "application/json")

    if DEBUG:
        print("\n--- REQUEST ---")
        print(f"POST {API_URL}")
        print(json.dumps(payload, indent=2))

    with urllib.request.urlopen(req) as resp:
        raw = resp.read()

    if DEBUG:
        print("--- RESPONSE ---")
        print(json.dumps(json.loads(raw), indent=2))
        print("--- END ---\n")

    data = json.loads(raw)

    # Some models (like this Gemma build) return their internal reasoning
    # in a separate "thinking" field, distinct from the actual reply in
    # "content". We just print it for visibility; the agent loop only
    # acts on "content".
    thinking = data["message"].get("thinking")
    if thinking:
        print(f"[thinking] {thinking}")

    return data["message"]["content"].strip()


# --- the agent loop ------------------------------------------------------

def run_agent(user_input, max_steps=5):
    # `messages` is the running conversation we send back to the model
    # every step, growing with each TOOL/OBSERVATION pair so the model
    # has full context of what it already tried.
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_steps):
        reply = call_llm(messages)  # THINK
        print(f"[agent] {reply}")

        # Some models don't reliably stick to "one line only" and cram
        # extra TOOL:/ANSWER: lines into the same reply. We only ever
        # act on the first line, so a stray second line can't get
        # swallowed into the tool's input by mistake.
        first_line = reply.strip().splitlines()[0]

        if first_line.startswith("ANSWER:"):
            return first_line[len("ANSWER:"):].strip()

        if first_line.startswith("TOOL:"):
            # Parse "TOOL: calculator 2 + 2" into name="calculator",
            # tool_input="2 + 2".
            rest = first_line[len("TOOL:"):].strip()
            name, _, tool_input = rest.partition(" ")

            if name not in TOOLS:
                observation = f"error: unknown tool '{name}'"
            else:
                observation = TOOLS[name](tool_input)  # ACT
            print(f"[tool:{name}] {observation}")

            # OBSERVE: feed the tool's result back in as a new "user"
            # turn so the model can read it on the next loop iteration.
            # We echo back only the first line, not the full (possibly
            # multi-line) reply, so the model doesn't see its own
            # malformed extra lines reflected back at it.
            messages.append({"role": "assistant", "content": first_line})
            messages.append({"role": "user", "content": f"OBSERVATION: {observation}"})
            continue

        # Model didn't follow either format - just surface whatever it
        # said rather than looping forever.
        return reply

    return "agent gave up after too many steps"


if __name__ == "__main__":
    question = input("Ask something (e.g. 'what is 12 * 7, then tell me the time'): ")
    print("\nFinal answer:", run_agent(question))

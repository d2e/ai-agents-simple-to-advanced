"""
A harness: the reusable runtime around the think/act/observe loop,
factored out instead of copy-pasted into every script.

Every tutorial since 01-basics has quietly been its own bespoke
harness - a loop, a tool registry, and whatever plugins (memory,
approval gates) that particular tutorial needed baked directly in.
This is the same loop, but pulled out into one small class where
tools, memory, and an approval gate are all swappable parts you pass
in, instead of code you rewrite. This is also basically what a
framework (LangChain, CrewAI, ...) *is*, underneath its own API -
seeing it built by hand here is what makes it obvious what a
framework is actually buying you in 19-frameworks.
"""

import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"


def call_llm(model, messages, tool_schemas):
    payload = {"model": model, "messages": messages, "tools": tool_schemas, "stream": False}
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


class Harness:
    """The reusable part: think -> act -> observe, wired through
    whichever plugins (memory, approval_gate) were passed in - the loop
    itself never changes no matter how it's configured."""

    def __init__(self, model, tools, tool_schemas, memory=None, approval_gate=None):
        self.model = model
        self.tools = tools                      # {name: function}
        self.tool_schemas = tool_schemas         # JSON schema list, sent to the model
        self.memory = memory if memory is not None else []
        # Passing the SAME list into two Harness instances (or two .run()
        # calls) is what makes memory persist - the harness doesn't do
        # anything special for that, it's just whoever owns the list.
        self.approval_gate = approval_gate or set()  # tool names needing human approval

    def run(self, user_input, max_steps=5):
        self.memory.append({"role": "user", "content": user_input})

        for _ in range(max_steps):
            message = call_llm(self.model, self.memory, self.tool_schemas)  # THINK
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                self.memory.append(message)
                return message["content"]

            self.memory.append(message)
            for call in tool_calls:
                name = call["function"]["name"]
                args = call["function"]["arguments"]

                if name in self.approval_gate:
                    answer = input(f"[approval] run {name}({args})? [y/N]: ").strip().lower()
                    if answer != "y":
                        print(f"[denied] {name}")
                        self.memory.append({"role": "tool", "content": "denied by user"})
                        continue

                if name not in self.tools:
                    result = f"error: unknown tool '{name}'"
                else:
                    result = self.tools[name](**args)  # ACT
                print(f"[tool:{name}] {result}")
                self.memory.append({"role": "tool", "content": str(result)})  # OBSERVE

        return "agent gave up after too many steps"


# --- tools, same shape as earlier tutorials ---------------------------

import datetime  # noqa: E402 (kept near where it's used, for a smaller diff)


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
    return f"email sent to {to} (subject: {subject!r})"


TOOLS = {"calculator": calculator, "get_time": get_time, "send_email": send_email}

TOOL_SCHEMAS = [
    {
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


if __name__ == "__main__":
    print("=== plain harness: no approval gate, fresh memory each run ===")
    plain = Harness(model=MODEL, tools=TOOLS, tool_schemas=TOOL_SCHEMAS)
    print("answer:", plain.run("what is 12 * 7?"))

    print("\n=== guarded harness: same loop, send_email now needs approval ===")
    guarded = Harness(
        model=MODEL, tools=TOOLS, tool_schemas=TOOL_SCHEMAS,
        approval_gate={"send_email"},
    )
    print("answer:", guarded.run("email jane@example.com subject Hi body 'Hello there'"))

    print("\n=== persistent harness: same loop, memory reused across two .run() calls ===")
    shared_memory = []
    persistent = Harness(model=MODEL, tools=TOOLS, tool_schemas=TOOL_SCHEMAS, memory=shared_memory)
    persistent.run("my favorite color is teal")
    print("answer:", persistent.run("what is my favorite color?"))

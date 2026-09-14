"""
Streaming: print tokens as they arrive, instead of waiting for the
whole reply.

Every earlier example set stream: false and waited for one full JSON
response. Here we set stream: true - Ollama then sends back a series
of small JSON objects, one per line, each carrying a tiny piece of the
reply. We print each piece immediately as it shows up, and only stop
once a chunk says "done": true.
"""

import json
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"


def stream_reply(messages):
    payload = {"model": MODEL, "messages": messages, "stream": True}
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, method="POST")
    req.add_header("content-type", "application/json")

    full_reply = ""
    with urllib.request.urlopen(req) as resp:
        # Each line of the response body is its own complete JSON
        # object - iterating the response object gives us one line
        # at a time, as they arrive over the network.
        for line in resp:
            line = line.strip()
            if not line:
                continue

            chunk = json.loads(line)
            if DEBUG:
                print(f"\n[chunk] {chunk}")

            piece = chunk["message"]["content"]
            print(piece, end="", flush=True)  # flush so it shows up immediately
            full_reply += piece

            if chunk.get("done"):
                break

    print()  # newline once the stream finishes
    return full_reply


if __name__ == "__main__":
    question = input("Ask something (e.g. 'write a 3 line poem about the ocean'): ")
    messages = [{"role": "user", "content": question}]
    print("agent: ", end="", flush=True)
    stream_reply(messages)

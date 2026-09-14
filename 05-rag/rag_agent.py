"""
RAG: retrieval augmented generation.

Instead of hoping the model already knows an answer, we look up
relevant text ourselves and paste it into the prompt before asking the
question. This teaches the model facts it was never trained on (or
reminds it of things buried in a large private document set) without
any fine-tuning - just better prompting.

Still zero third-party libraries: embeddings come from Ollama's
/api/embeddings endpoint (plain HTTP), and similarity is a few lines
of pure-Python math - no numpy, no vector database.
"""

import json
import math
import os
import urllib.request

API_URL = "http://localhost:11434/api/chat"
EMBED_URL = "http://localhost:11434/api/embeddings"
MODEL = "gemma4:latest"
EMBED_MODEL = "nomic-embed-text"
DEBUG = os.environ.get("DEBUG") == "1"

# A tiny "knowledge base" the model was never trained on - made-up
# facts about a fictional company. If the agent answers correctly,
# it's because retrieval actually found the right fact, not because
# the model guessed.
KNOWLEDGE_BASE = [
    "Zylo Corp's coffee machine is on the 3rd floor, next to the elevators.",
    "Zylo Corp employees get every third Friday off, called Flex Friday.",
    "Zylo Corp's VPN password rotates automatically every 90 days.",
    "Zylo Corp's main office mascot is a robot named Bipsy.",
    "Zylo Corp was founded in 2019 by three former graphic designers.",
]


def embed(text):
    body = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(EMBED_URL, data=body, method="POST")
    req.add_header("content-type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["embedding"]


def cosine_similarity(a, b):
    # How similar two vectors point, regardless of length: 1.0 means
    # identical direction, 0.0 means unrelated, -1.0 means opposite.
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# Embedding every KB entry on every query would be wasteful - a real
# system precomputes and stores these once (e.g. in a vector DB). We
# just cache them in memory the first time they're needed.
_kb_embeddings = None


def get_kb_embeddings():
    global _kb_embeddings
    if _kb_embeddings is None:
        _kb_embeddings = [embed(doc) for doc in KNOWLEDGE_BASE]
    return _kb_embeddings


def retrieve(query, k=2):
    """Return the k most relevant knowledge base entries for `query`."""
    query_vec = embed(query)
    doc_vecs = get_kb_embeddings()

    scored = []
    for doc, doc_vec in zip(KNOWLEDGE_BASE, doc_vecs):
        score = cosine_similarity(query_vec, doc_vec)
        scored.append((score, doc))
    scored.sort(reverse=True)  # tuples sort by score first, highest first

    if DEBUG:
        print("--- RETRIEVAL SCORES ---")
        for score, doc in scored:
            print(f"{score:.3f}  {doc}")
        print("--- END ---")

    return [doc for _, doc in scored[:k]]


def generate_answer(question):
    context_docs = retrieve(question)
    context = "\n".join(f"- {doc}" for doc in context_docs)

    # This is the entire "augmentation" step: stuff retrieved text into
    # the prompt and tell the model to stick to it. No tools, no loop -
    # RAG is a preprocessing step in front of a single generation call.
    prompt = (
        "Answer the question using ONLY the context below. "
        "If the context doesn't contain the answer, say you don't know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
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

    message = json.loads(raw)["message"]
    thinking = message.get("thinking")
    if thinking:
        print(f"[thinking] {thinking}")
    return message["content"].strip()


if __name__ == "__main__":
    question = input(
        "Ask something about Zylo Corp (e.g. 'what floor is the coffee machine on?'): "
    )
    print("\nAnswer:", generate_answer(question))

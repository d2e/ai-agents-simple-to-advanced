# 05 - RAG: Retrieval Augmented Generation

Instead of hoping the model already knows something, look it up
yourself and paste it into the prompt. `rag_agent.py` embeds a tiny
made-up "knowledge base" (facts about a fictional company, so you can
tell whether an answer came from retrieval or a guess), finds the most
relevant entries for a question via cosine similarity, and stuffs them
into the prompt before asking the model.

No vector database, no numpy — embeddings come from Ollama's
`/api/embeddings` endpoint, and similarity is plain-Python math.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama,
plus an embedding model:

```bash
ollama pull nomic-embed-text
```

## Run

```bash
python3 rag_agent.py
# try: what floor is the coffee machine on?
# try: who founded Zylo Corp?
# try: who is the CEO of Microsoft?   <- not in the knowledge base
DEBUG=1 python3 rag_agent.py   # see retrieval scores + the augmented prompt
```

## Example

```
Ask something: what floor is the coffee machine on?
Answer: The coffee machine is on the 3rd floor.

Ask something: who is the CEO of Microsoft?
Answer: I don't know
```

The second answer proves it's not guessing — that fact isn't in
`KNOWLEDGE_BASE`, so retrieval finds nothing relevant and the model
(told to stick to context) admits it doesn't know.

## What's actually happening

1. `embed(text)` turns text into a vector (a list of numbers).
2. `cosine_similarity(a, b)` scores how alike two vectors point —
   that's the entire "search".
3. `retrieve(query)` embeds the question, scores it against every KB
   entry, returns the top matches.
4. `generate_answer()` pastes those matches into the prompt and asks
   the model to answer using *only* that context.

No agent loop, no tools — RAG here is just a lookup step bolted in
front of a single generation call.

# AI Agents: Simple to Advanced

Learning AI agents from scratch — no frameworks, mostly stdlib Python,
so the agent loop stays visible. Each folder is a self-contained step.

| Folder | Topic | Status |
| --- | --- | --- |
| [`01-basics`](./01-basics) | Core agent loop: think → act → observe | done |
| [`02-tool-use`](./02-tool-use) | Structured (JSON) tool calls, native API | done |
| [`03-memory`](./03-memory) | Conversation memory / state across turns | done |
| `04-multi-agent` | Agents collaborating or delegating | planned |
| `05-frameworks` | Same ideas rebuilt with a framework | planned |

## Setup: local model via Ollama

```bash
brew install ollama       # or https://ollama.com/download
ollama serve              # skip if already running
ollama pull gemma4        # default model used by the examples
```

Any pulled model works — change the `MODEL` constant at the top of
each script (`llama3.1:8b`, `qwen2.5:14b`, etc). To use a hosted API
instead, swap `API_URL`/`MODEL` and adjust `call_llm()`'s request
shape — everything's plain HTTP, no SDK lock-in.

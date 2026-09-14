# AI Agents: Simple to Advanced

Learning AI agents from scratch — no frameworks, mostly stdlib Python,
so the agent loop stays visible. Each folder is a self-contained step.

| Folder | Topic | Status |
| --- | --- | --- |
| [`01-basics`](./01-basics) | Core agent loop: think → act → observe | done |
| [`02-tool-use`](./02-tool-use) | Structured (JSON) tool calls, native API | done |
| [`03-memory`](./03-memory) | Conversation memory / state across turns | done |
| [`04-multi-agent`](./04-multi-agent) | Agents collaborating or delegating | done |
| [`05-rag`](./05-rag) | Retrieval augmented generation | done |
| [`06-context-compaction`](./06-context-compaction) | Summarize/trim history once it gets long | done |
| [`07-streaming`](./07-streaming) | Token-by-token output | done |
| [`08-guardrails`](./08-guardrails) | Validate output, retry on bad shape | done |
| [`09-human-in-the-loop`](./09-human-in-the-loop) | Pause for approval before risky tool calls | done |
| [`10-evaluation`](./10-evaluation) | Automated pass/fail checks, not eyeballing output | done |
| `11-prompt-injection` | Untrusted tool/RAG content trying to hijack the agent | planned |
| `12-frameworks` | Same ideas rebuilt with a framework | planned |

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

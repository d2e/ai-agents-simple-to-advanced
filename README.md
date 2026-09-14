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
| [`11-prompt-injection`](./11-prompt-injection) | Untrusted tool/RAG content trying to hijack the agent | done |
| [`12-intent-routing`](./12-intent-routing) | Classify intent first, dispatch to a dedicated handler | done |
| [`13-planning`](./13-planning) | Plan the whole task upfront vs. reacting step by step | done |
| [`14-stateful-coordination`](./14-stateful-coordination) | Agents sharing a common workspace, not just final answers | done |
| [`15-artifact-references`](./15-artifact-references) | Reference large tool output by ID instead of inlining it | done |
| [`16-token-budget-context`](./16-token-budget-context) | Assemble context by token budget, not message count | done |
| [`17-resilience`](./17-resilience) | Retry with backoff - only for failures a retry can fix | done |
| `18-frameworks` | Same ideas rebuilt with a framework | planned |

Observability and cost tracking aren't covered as standalone stdlib
tutorials — most frameworks provide these out of the box (tracing,
per-call token/cost accounting), so they'll be covered as part of
`18-frameworks` instead of reimplemented from scratch here.

## Suggested reading paths

Folders are numbered in the order they were added (roughly increasing
complexity), but related concepts ended up spread out. If you want to
go deeper on one theme instead of reading start to finish:

- **Context management** — [`03-memory`](./03-memory) →
  [`06-context-compaction`](./06-context-compaction) →
  [`16-token-budget-context`](./16-token-budget-context) →
  [`15-artifact-references`](./15-artifact-references)
- **Multi-agent patterns** — [`04-multi-agent`](./04-multi-agent) →
  [`12-intent-routing`](./12-intent-routing) →
  [`14-stateful-coordination`](./14-stateful-coordination)
- **Safety & reliability** — [`08-guardrails`](./08-guardrails) →
  [`09-human-in-the-loop`](./09-human-in-the-loop) →
  [`11-prompt-injection`](./11-prompt-injection) →
  [`17-resilience`](./17-resilience)
- **Everything else** — [`05-rag`](./05-rag),
  [`07-streaming`](./07-streaming), [`10-evaluation`](./10-evaluation),
  [`13-planning`](./13-planning) each stand alone

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

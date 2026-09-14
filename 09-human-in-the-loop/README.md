# 09 - Human in the Loop

`02-tool-use` ran every tool call the model asked for automatically.
That's fine for a calculator, but not for anything with real
consequences. Here, tools listed in `RISKY_TOOLS` (just `send_email`,
simulated) pause for a y/n confirmation before running. If denied, the
model is told the action was denied — not why — so it reacts sensibly
instead of blindly retrying the same call.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 hitl_agent.py
# try: email jane@example.com subject Hi body "Hello there"
# then answer y or n when prompted
```

## Example — denied

```
Ask something: email jane@example.com subject Hi body "Hello there"
[approval needed] run send_email({'to': 'jane@example.com', 'subject': 'Hi', 'body': 'Hello there'})? [y/N]: n
[denied] send_email
[agent] The email could not be sent because you denied the request.
```

## Example — approved

```
[approval needed] run send_email(...)? [y/N]: y
[tool:send_email] email sent to jane@example.com (subject: 'Hi')
[agent] I have sent the email to jane@example.com with the subject "Hi" and the body "Hello there".
```

## What's actually happening

- `RISKY_TOOLS` is just a set of tool names — anything not in it runs
  automatically, same as `02-tool-use`.
- The approval check happens *before* the tool function ever runs, so
  a denial genuinely means nothing happened, not "it ran but we hid it."
- The observation sent back on denial (`"denied by user"`) is
  deliberately vague — enough for the model to explain the outcome,
  not so much that it starts negotiating or working around the human.

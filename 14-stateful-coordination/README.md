# 14 - Stateful Coordination

`04-multi-agent` treated each specialist as a black box: call it, get
text back, that's the only channel. Here, multiple specialist calls
all read and write the *same* shared workspace (`shared_state["facts"]`)
directly — each one sees exactly what earlier calls already
contributed, not a paraphrase relayed by an orchestrator.

Two `researcher()` calls add facts about a topic to the shared list;
`writer()` reads the whole accumulated list afterward and summarizes
it. This is the "blackboard" pattern — a shared workspace multiple
agents build up over one task.

## Setup

[Root README](../README.md#setup-local-model-via-ollama) for Ollama.

## Run

```bash
python3 coordination_agent.py
# try: honey bees
```

## Example

```
[researcher:diet] added 2 facts
    - Pollen is collected for protein and fats for the developing brood.
    - Bees can also process sugary liquid from certain fruits or sap.
[researcher:communication] added 2 facts
    - The waggle dance communicates direction and distance to a foraging patch.
    - Queen mandibular pheromones regulate worker behavior in the colony.

Summary: Honey bees rely on pollen and nectar (and occasionally fruit/sap
sugars) for nutrition, and coordinate as a colony through the waggle
dance and queen pheromone signaling.
```

Running two researchers on the *same* angle (`["diet", "diet"]`) shows
the mechanism clearly: the second call sees the first's facts already
in `shared_state` and is told not to repeat them — it produces
genuinely different facts instead of duplicates.

## What's actually happening

- `shared_state` is just a plain dict passed by reference — every
  specialist function mutates it directly, no return-value relay needed.
- `researcher()` reads `shared_state["facts"]` *before* generating, so
  later calls are aware of earlier ones — coordination through shared
  state, not through a coordinator re-explaining what happened.
- `writer()` never talks to `researcher()` — it only ever sees the
  final shared state, same as any other reader of a blackboard would.

"""
Self-improvement: the agent writes its own system prompt from its mistakes.

Every earlier tutorial had a system prompt *you* wrote and the agent was
stuck with. Here the agent fails a task, works out why, proposes a
general rule to avoid that failure, and keeps the rule only if it
measurably helps. The rules persist to disk, so each run starts smarter
than the last.

Nothing is being trained - the weights never change. "Learning" here is
entirely in-context: a growing set of rules prepended to the prompt. The
interesting constraint is that this only works when the failures share a
*common cause*, so one rule transfers to tasks the agent has never seen.

The task is letter counting ("how many r's in strawberry"). It's a toy,
but it's the clearest possible demo: the model reliably fails it, the
ground truth is `word.count(ch)` so the reward needs no judge, and every
failure has the same root cause - so a single rule fixes the whole class.
"""

import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:latest"
DEBUG = os.environ.get("DEBUG") == "1"

# Where learned rules persist between runs. Delete it to start from scratch.
RULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learned_rules.json")

# gemma4 has a built-in "thinking" mode that is ON by default. Left on, it
# already reasons its way around this failure and there is nothing left to
# learn - the whole curve would be flat. We pin it off to isolate the
# behaviour we want the agent to improve on its own.
THINK = False

# Ollama handles parallel requests, and a sequential run of ~50 calls on a
# local 8B model is a long wait. This is the only reason for the threads.
WORKERS = 4


# --- the task: deterministic reward, no LLM judge ---------------------------

# Split so we can prove the agent *generalizes* rather than memorizing. The
# test words are never shown during training.
TRAIN_WORDS = [
    ("mississippi", "s"), ("unsuccessfully", "s"), ("parallelogram", "l"),
    ("accommodation", "c"), ("bookkeeper", "e"), ("committee", "t"),
    ("possession", "s"), ("millennium", "l"),
]

VALIDATION_WORDS = [
    ("embarrassment", "r"), ("occurrence", "c"), ("questionnaire", "n"),
    ("hippopotamus", "p"), ("tennessee", "e"), ("aggressively", "g"),
]

TEST_WORDS = [
    ("strawberry", "r"), ("counterrevolutionary", "o"), ("entrepreneurship", "e"),
    ("disestablishment", "s"), ("onomatopoeia", "o"), ("sesquipedalian", "e"),
    ("antidisestablish", "i"), ("irresistible", "i"), ("bureaucracy", "u"),
    ("conscientious", "c"),
]

BASE_PROMPT = (
    "You count letters in words. "
    "End your reply with the count on its own last line, exactly as: #### <number>"
)


def expected_answer(word, char):
    """Ground truth. This is why the reward needs no model to judge it."""
    return word.count(char)


def parse_count(text):
    """Pull the integer out of the '#### N' marker, else the last number seen."""
    tail = text.split("####")[-1] if "####" in text else text
    numbers = re.findall(r"\d+", tail)
    return int(numbers[0]) if numbers else -1


# --- the model call ----------------------------------------------------------

def call_llm(system, user, temperature=0):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "think": THINK,
        # Answering uses temperature 0, so a score change is the rule working
        # rather than sampling luck. Reflection overrides this - see reflect().
        "options": {"temperature": temperature},
    }
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, method="POST")
    req.add_header("content-type", "application/json")

    if DEBUG:
        print("\n--- REQUEST ---")
        print(json.dumps(payload, indent=2))

    with urllib.request.urlopen(req, timeout=600) as resp:
        raw = resp.read()

    if DEBUG:
        print("--- RESPONSE ---")
        print(json.dumps(json.loads(raw), indent=2))
        print("--- END ---\n")

    return json.loads(raw)["message"].get("content") or ""


# --- 1. attempt: answer the task using whatever rules we've learned so far ---

def build_prompt(rules):
    """The learned rules ARE the improvement - they're just prompt text."""
    if not rules:
        return BASE_PROMPT
    numbered = "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1))
    return f"{BASE_PROMPT}\n\nRules you learned from past mistakes:\n{numbered}"


def attempt(task, rules):
    word, char = task
    reply = call_llm(
        build_prompt(rules),
        f"How many times does the letter '{char}' appear in '{word}'?",
    )
    got = parse_count(reply)
    return {
        "word": word,
        "char": char,
        "got": got,
        "expected": expected_answer(word, char),
        "reply": reply,
    }


def score(tasks, rules):
    """Run a whole task set and return (accuracy, individual results)."""
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda t: attempt(t, rules), tasks))
    # 2. reward: exact match, 1 or 0. No partial credit, no judge model.
    correct = sum(r["got"] == r["expected"] for r in results)
    return correct / len(results), results


# --- 3. reflect: turn concrete failures into one general rule ---------------

def reflect(failures, rules, rejected):
    """
    Ask the model why it failed and for a rule that prevents a repeat.

    Two things here are load-bearing, both learned the hard way:

    - `temperature=0.8`. At 0 the model sees the same failures every round
      and proposes the byte-identical rule every round, so rounds 2 and 3
      are pure waste. Reflection is a *search* for a rule that works, and
      search needs variation.
    - Rejected candidates are fed back in. Otherwise the search has no
      memory of its own dead ends and keeps re-proposing them.

    The prompt also demands a step-by-step *procedure*. Asked loosely, the
    model returns a restatement of the goal ("be sure to count every
    instance"), which reliably measures as no better than nothing.
    """
    shown = "\n".join(
        f"- '{f['char']}' in '{f['word']}': you said {f['got']}, correct was {f['expected']}"
        for f in failures
    )
    existing = "\n".join(f"- {r}" for r in rules) or "- (none yet)"
    dead_ends = "\n".join(f"- {r}" for r in rejected) or "- (none yet)"

    return call_llm(
        "You improve another AI's instructions by diagnosing its mistakes.",
        f"An AI counting letters in words got these wrong:\n{shown}\n\n"
        f"Rules it already follows:\n{existing}\n\n"
        f"Rules already tried and measured as NOT helping - do not repeat "
        f"these or reword them:\n{dead_ends}\n\n"
        "Diagnose the root cause, then write ONE new instruction that prevents "
        "this class of mistake on ANY word.\n"
        "Requirements:\n"
        "- Describe a concrete step-by-step PROCEDURE to follow while working.\n"
        "- Do NOT simply restate the goal ('count carefully', 'be accurate', "
        "'include every instance') - that is useless, it already tries to do that.\n"
        "- Must be a general method, NOT facts about these specific words.\n"
        "Reply with the instruction text only - one or two sentences, no preamble.",
        temperature=0.8,
    ).strip()


# --- 4. keep or discard: the step that makes this learning, not graffiti ----

def validate(candidate, rules):
    """
    Measure a candidate rule on a held-out set before adopting it.

    Without this gate the agent cheerfully accumulates plausible-sounding
    rules that do nothing, or actively hurt by cluttering the prompt. The
    model proposing a rule is not evidence the rule works - measuring is.
    """
    accuracy, _ = score(VALIDATION_WORDS, rules + [candidate])
    return accuracy


# --- persistence: this is what makes run #2 start smarter than run #1 -------

def load_rules():
    if not os.path.exists(RULES_FILE):
        return []
    with open(RULES_FILE) as fh:
        return json.load(fh)


def save_rules(rules):
    with open(RULES_FILE, "w") as fh:
        json.dump(rules, fh, indent=2)


# --- the improvement loop ----------------------------------------------------

def improve(rules, rounds=2, candidates_per_round=3):
    """
    Propose several rules per round and adopt the best one that beats the bar.

    Proposing just one rule per round makes the whole run hostage to a
    single bad draw. Generating a few and keeping the best measured one
    makes this an actual search rather than a coin flip.
    """
    baseline, _ = score(VALIDATION_WORDS, rules)
    print(f"validation baseline with {len(rules)} rule(s): {baseline:.0%}\n")
    rejected = []

    for round_number in range(1, rounds + 1):
        print(f"--- round {round_number} ---")
        accuracy, results = score(TRAIN_WORDS, rules)
        failures = [r for r in results if r["got"] != r["expected"]]
        print(f"  train: {accuracy:.0%} ({len(failures)} failed)")

        if not failures:
            print("  nothing left to learn from on the training set\n")
            break

        for f in failures:
            print(f"    MISS '{f['char']}' in {f['word']}: {f['got']} != {f['expected']}")

        scored = []
        for n in range(1, candidates_per_round + 1):
            candidate = reflect(failures, rules, rejected)
            candidate_accuracy = validate(candidate, rules)
            print(f"  candidate {n}: {candidate_accuracy:.0%} | {candidate}")
            scored.append((candidate_accuracy, candidate))

        best_accuracy, best_rule = max(scored, key=lambda pair: pair[0])

        # Strictly better, not merely equal - a rule that ties is just prompt
        # clutter, and clutter has its own cost on later tasks.
        if best_accuracy > baseline:
            print(f"  -> KEEP ({baseline:.0%} -> {best_accuracy:.0%})\n")
            rules.append(best_rule)
            save_rules(rules)
            baseline = best_accuracy
            rejected += [c for _, c in scored if c != best_rule]
        else:
            print(f"  -> DISCARD all (none beat {baseline:.0%})\n")
            rejected += [c for _, c in scored]

    return rules


if __name__ == "__main__":
    rules = load_rules()
    print(f"loaded {len(rules)} learned rule(s) from previous runs\n")

    # Measure on the held-out test set before and after, so the number at the
    # end is generalization to unseen words - not memorization of training ones.
    before, _ = score(TEST_WORDS, rules)
    print(f"TEST accuracy before this run: {before:.0%}\n")

    rules = improve(rules)

    after, _ = score(TEST_WORDS, rules)
    print("=" * 60)
    print(f"TEST accuracy: {before:.0%} -> {after:.0%}  (held-out words, never trained on)")
    print(f"rules learned: {len(rules)}")
    for i, rule in enumerate(rules, 1):
        print(f"  {i}. {rule}")
    print(f"\nsaved to {os.path.basename(RULES_FILE)} - run again to continue improving")

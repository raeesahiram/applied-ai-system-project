# PawPal+ AI Edition

## Demo
[Watch the walkthrough](https://www.loom.com/share/a684b2225906453287237e56284b3f71)

---

A pet care scheduling app built on top of a rule-based system from a previous assignment, now extended with a Google Gemini AI assistant that explains the generated schedule in plain English.

---

## Original Project

This extends PawPal+ (Module 2), which was a rule-based pet care scheduler. The original let a pet owner enter their pets and tasks, then automatically built a daily schedule based on time availability and priority. It used a greedy algorithm, had conflict detection, and output a plain-text plan summary. It worked well but the output was pretty mechanical — no reasoning, no natural language, just raw data.

---

## What This Project Does

PawPal+ AI Edition adds a Gemini-powered AI assistant into the pipeline. Once the scheduler builds the daily plan, it gets passed to the AI with context about the owner, pets, and available time. Gemini then generates a natural-language explanation — why tasks were prioritized the way they were, what got left out, and some suggestions.

The point is that most scheduling tools make you interpret the output yourself. Adding an AI explanation step makes it actually readable for someone who isn't looking at code.

What this project covers:
- real API integration with Google Gemini (gemini-2.5-flash)
- agentic workflow: the AI reasons over structured system output, not freeform text
- logging, error handling, and a graceful fallback if the API goes down
- extending a working codebase without breaking what was already there

---

## Architecture

```
Pet Owner (User)
      |
      v
Streamlit UI  ──────────────────────────────────────────────┐
      |                                                      |
      v                                                      |
PawPal+ Logic (pawpal_system.py)                            |
  ├── Task / Pet / Owner models                             |
  ├── Scheduler (greedy priority-based planner)            |
  └── Conflict detection + rule-based explanation          |
      |                                                      |
      v                                                      |
AI Assistant (ai_assistant.py)                              |
  ├── Calls Google Gemini API with schedule context        |
  ├── score_response() scores output 0.0-1.0               |
  └── Returns natural-language reasoning ─────────────────>|
                                                             |
Evaluator / Tests (tests/test_pawpal.py)                   |
  └── Validates scheduling logic + AI output consistency   |
```

Two layers in sequence:
- Rule-based layer: the original scheduler builds the plan deterministically. Fast, predictable, testable.
- AI layer: Gemini gets the plan as context and explains it. It doesn't change the schedule, it just narrates it.

Keeping these separate means the scheduling logic stays auditable and the user-facing output is actually readable.

A more detailed Mermaid diagram of the full system (including the fallback path, score_response, and test layer) is in assets/system_diagram.mmd.

---

## Setup

You need Python 3.10+ and a free Gemini API key from Google AI Studio. When creating the key, pick "Create API key in new project" so you get free tier quota.

1. Clone the repo and go to the project folder

```bash
git clone <your-repo-url>
cd applied-ai-system-project
```

2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Create a .env file with your API key

```
GEMINI_API_KEY=your-api-key-here
```

5. Run the app

```bash
streamlit run app.py
```

Opens at http://localhost:8501.

6. Run tests

```bash
python -m pytest
```

---

## Sample Interactions

Example 1 is a real live output captured during development. Examples 2 and 3 show expected behavior for different scenarios but weren't captured live.

---

### Example 1 — verified live output

Input (entered through the Streamlit UI):
- Owner: Jordan, 90 minutes available
- Pet: Mochi
- Tasks: Medication (10 min, priority 5), Morning walk (30 min, priority 5), Litter cleaning (15 min, priority 4)

Rule-based schedule output:
```
Schedule for 2026-04-23:
- Medication (10 minutes, priority 5)
- Morning walk (30 minutes, priority 5)
- Litter cleaning (15 minutes, priority 4)
Total scheduled minutes: 55
Remaining available minutes: 35
```

AI explanation (real Gemini output):
> Hi Jordan! Here's a warm look at Mochi's PawPal+ plan for today, April 23rd. The schedule has been thoughtfully created to ensure Mochi's most essential needs are covered. Your 10 minutes for Medication and the 30-minute Morning walk were given the highest priority (priority 5) because these are fundamental for Mochi's health, routine, and overall well-being. The 15 minutes for Litter cleaning is also super important for hygiene and Mochi's comfort, making it a high priority (priority 4) too.
>
> It looks like these essential daily tasks total 55 minutes, which means no crucial care activities were left out of today's schedule from the items generated! The system makes sure that core care like medication, necessary exercise, and cleanliness are always prioritized and included when your available time allows.
>
> The great news is you have a wonderful 35 minutes remaining from your available 90 minutes today! This is a perfect opportunity for some extra bonding time with Mochi. You could extend your Morning walk if Mochi is really enjoying the outdoors, or perhaps use that time for a dedicated playtime session, a gentle grooming brush, or even working on a fun new trick together. Enjoy your day with Mochi!

Reliability score: 1.0 / 1.0 (all four checks passed)

---

### Example 2 — overloaded schedule with conflicts

Input:
- Owner: Alex, 60 minutes available
- Pet: Fido (dog)
- Tasks: Vet appointment (45 min, priority 5, due 10:00 AM), Morning walk (30 min, priority 4, due 10:15 AM), Feeding (10 min, priority 3)

Rule-based schedule output:
```
Schedule for 2026-04-23:
- Vet appointment (45 minutes, priority 5)
- Feeding (10 minutes, priority 3)
Total scheduled minutes: 55
Remaining available minutes: 5
WARNING: Task 'Vet appointment' (10:00-10:45) overlaps with 'Morning walk' (10:15-10:45).
```

Expected AI behavior: the AI gets the conflict warning as part of its context, so it should explain why the walk was dropped, flag the time overlap, and suggest rescheduling it.

---

### Example 3 — two pets, recurring tasks

Input:
- Owner: Sam, 120 minutes available
- Pet 1: Luna (cat) — Feeding (10 min, priority 5, recurring daily), Litter cleaning (15 min, priority 4)
- Pet 2: Biscuit (dog) — Morning walk (30 min, priority 5, recurring daily), Training session (20 min, priority 3)

Rule-based schedule output:
```
Schedule for 2026-04-23:
- Feeding (10 minutes, priority 5)
- Morning walk (30 minutes, priority 5)
- Litter cleaning (15 minutes, priority 4)
- Training session (20 minutes, priority 3)
Total scheduled minutes: 75
Remaining available minutes: 45
```

Expected AI behavior: note that everything fit, explain priority ordering across two pets, and mention that recurring tasks auto-generate the next occurrence when marked complete.

---

## Design Decisions

Why Gemini free tier instead of Claude or GPT?

This is a student project with no budget. Gemini has a free tier through Google AI Studio that's enough for development and demos. The actual API call is just sending a prompt and reading a text response, which is the same across providers — swapping models would take one line change.

Why gemini-2.5-flash specifically?

During development, gemini-2.0-flash and gemini-2.0-flash-lite both hit quota errors on the free tier. gemini-2.5-flash was the first model that actually worked. The model name is one constant in ai_assistant.py.

Why keep the rule-based scheduler instead of having AI do the scheduling?

The rule-based layer is deterministic and testable. The same inputs always produce the same output, which is what makes it possible to write reliable tests. If you let an LLM do the scheduling it introduces unpredictability, latency, and API cost on every schedule generation. The AI is only used for the explanation step where it actually adds value — turning structured data into something readable.

Why greedy algorithm instead of optimal knapsack?

The greedy approach is O(n) and easy to understand — pick the highest priority tasks first until you run out of time. An optimal solution would try all combinations but for a daily pet care schedule with under 20 tasks the difference is negligible. I also just felt it was overkill for this scope, same as the original project.

Why log every AI call?

AI responses are non-deterministic so you can't just run the test suite and be done. Logging every request and response to pawpal_ai.log means you have an audit trail for debugging and can track whether output quality is drifting over time.

Tradeoffs:

| Decision | Benefit | Cost |
|---|---|---|
| AI explains schedule, doesn't build it | Predictable scheduling, testable | AI has no influence over what gets scheduled |
| gemini-2.5-flash free tier | No cost | Rate limits, occasional 503s |
| Greedy scheduler | Simple, fast, auditable | Not globally optimal |
| Logging to pawpal_ai.log | Reproducible, debuggable | Disk usage over time |
| Graceful fallback on API failure | App never crashes | User sees rule-based text instead of AI output |

---

## Testing

Evaluation harness — run python evaluate.py to test the full pipeline on 4 predefined scenarios:

```
==============================================================
  PawPal+ AI Evaluation Harness
==============================================================
  Scenario                   Sched   Conf     AI   Pass
--------------------------------------------------------------
  Standard plan                3/3   1.00    yes   PASS
  Overloaded schedule          1/3   1.00    yes   PASS
  Time conflict                2/2   1.00    yes   PASS
  Multi-pet / recurring        4/4   1.00    yes   PASS
--------------------------------------------------------------
  Result : 4/4 passed
  Avg confidence score : 1.00
  AI used  : 4/4 scenarios  (all live Gemini responses)
==============================================================
```

Each scenario runs the whole pipeline: schedule generation, conflict detection, Gemini explanation, score_response fact-check. Passing threshold is 0.75.

Unit tests — run python -m pytest:

| Category | Tests | Result |
|---|---|---|
| Scheduler logic | 6 | 6 / 6 passed |
| AI module unit tests (no API calls) | 7 | 7 / 7 passed |
| Live AI reliability (real Gemini call) | 1 | Skipped — Gemini 503 during high server demand |

13 / 13 executable tests passed. 1 skipped due to Gemini being temporarily unavailable, not a code issue.

Reliability scoring:

Every AI response gets scored 0.0-1.0 by score_response in ai_assistant.py. It checks four things:
- owner name appears in the response
- at least one pet name appears
- at least one task title appears
- response length is between 50 and 2000 characters

Each check is worth 0.25. Passing is anything 0.75 or above. The live output in Example 1 scored 1.0. The score gets written to pawpal_ai.log on every run.

What worked: all the deterministic logic passed cleanly. The error handling caught a real 503 from Gemini, logged it, and fell back without crashing. Restructuring the prompt to include owner name, pet names, and task context made a big difference in output quality compared to just dumping the raw schedule text.

What didn't work at first: the first prompt just sent the raw explain_plan() output and responses were generic — no pet or task names mentioned. Gemini also kept failing with quota errors on gemini-2.0-flash and gemini-2.0-flash-lite before I switched to gemini-2.5-flash. The live AI test also hit a 503 during the initial run and had to be updated to skip gracefully instead of reporting a false failure.

What I learned: you can't assert exact string equality on AI responses the way you would with normal code. The same prompt produces different phrasing every time. Instead you check for key facts being present and set a minimum threshold. That's the approach I used for the reliability scorer.

---

## Prompt Specialization (stretch feature)

ai_assistant.py has two prompt modes controlled by the specialized parameter on explain_schedule:

- Baseline (specialized=False): open-ended instructions, no examples. Gemini picks its own structure.
- Specialized (specialized=True, the default): two few-shot examples are injected into the prompt that show the exact structure I want — greet the owner by name, explain priority order, address skipped tasks, close with "One tip:".

Run python compare_modes.py to see both side by side on the same input. Real output from a live run:

```
  Metric                           Baseline   Specialized
  ────────────────────────────────────────────────────────
  Paragraphs                              3             3
  Word count                            212           150 ◄
  Opens with owner name                True          True
  Mentions pet name                    True          True
  Mentions all tasks                   True         False ◄
  Closes with tip                     False          True ◄
  Reliability score                     1.0           1.0

  3 metric(s) changed between modes.
```

The specialized prompt was more concise (62 fewer words), always closed with a concrete tip (baseline never did), and didn't mention Grooming since it wasn't actually scheduled — all from the few-shot examples constraining the output format.

---

## Responsible AI

Limitations and biases:

The AI has no actual pet care knowledge. It's a general-purpose model reasoning about a schedule it didn't create. If you give it bad data — like a 2-minute vet appointment — it'll just explain that as if it's normal instead of flagging it. It also has no memory between sessions, so it can't notice patterns like a task getting skipped repeatedly or anything changing over time. The prompts are in English and assume a standard household pet, so it probably works less well for anything outside that.

Could it be misused?

The most realistic issue is someone treating the AI explanation as actual veterinary advice. The AI has no medical knowledge and shouldn't be used that way. To help with this the app labels the output as "AI Assistant" (not "recommendation" or "diagnosis") and always shows the rule-based schedule separately so it's clear the AI is commenting on the plan, not making it.

There's also a prompt injection risk — if someone puts instruction-like text into a task title or pet name it could potentially manipulate the AI response. The current system doesn't sanitize user input before it goes into the prompt, which would need to be fixed before any real deployment.

What surprised me during testing:

The "limit: 0" in Gemini's quota error doesn't actually mean the daily limit is zero — it can show up for a per-minute rate limit too. I spent a while thinking my API key had no access when the real issue was I was making too many calls too fast. Switching models and waiting out the rate limit window fixed it.

The other thing that surprised me was how much the prompt structure mattered. The first version just sent the raw schedule text and responses were vague with no specifics. Adding the owner's name, the pet names, and the available time budget made responses specific and actually useful on the very next call. The model didn't change, just the input.

Collaboration with AI during this project:

I used Claude Code throughout — for designing the module structure, writing the Gemini integration, building tests, and debugging API errors.

A suggestion that was genuinely helpful: when building the reliability tests, it suggested scoring responses with a fact-checking function (score_response) instead of checking exact string equality. That was the right call because LLM output changes phrasing every run even when it's correct. The soft-assertion approach — check that key facts are present, set a minimum threshold — is actually how production AI evaluation works, and I wouldn't have thought to frame it that way.

A suggestion that was wrong: the initial integration used the google-generativeai Python package, which was suggested as the standard Gemini SDK. When I ran the code it immediately threw a FutureWarning saying the package was fully deprecated and to switch to google-genai. The AI's training data was out of date and I had to find the fix from the actual warning message, not from the AI.

What I'd improve next:

The biggest thing missing is persistent state — right now everything resets when you refresh the page because Streamlit session state doesn't survive a reload. Adding a simple local database or JSON file to save pets and tasks between sessions would make it actually usable day-to-day. I'd also want to sanitize user input before it goes into the prompt to close the prompt injection risk mentioned above, and add partial overlap detection to the conflict checker since right now it only catches tasks that start at the exact same time.

---

## Project Structure

```
├── pawpal_system.py       # core classes: Task, Pet, Owner, Scheduler
├── ai_assistant.py        # Gemini integration, both prompt modes, reliability scorer
├── app.py                 # Streamlit UI
├── evaluate.py            # evaluation harness — 4 scenarios, scored summary
├── compare_modes.py       # baseline vs. specialized prompt comparison
├── main.py                # CLI demo (original project)
├── requirements.txt       # dependencies
├── .env                   # API key (gitignored)
├── .gitignore
├── pawpal_ai.log          # AI call log (auto-generated on first run)
├── assets/
│   └── system_diagram.mmd # architecture diagram
├── tests/
│   └── test_pawpal.py     # pytest suite
└── reflection.md          # original assignment reflection
```

---

## Author

Raeesah Iram — Applied AI Systems course. Extended from a rule-based scheduling assignment into an AI-augmented app.

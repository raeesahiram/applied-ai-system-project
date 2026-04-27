# Model Card — PawPal+ AI Edition

> Note: Full details for all sections below are also documented in README.md.

## Base Project
PawPal+ (Module 2) — a rule-based pet care scheduler using a greedy priority algorithm with conflict detection and plain-text plan output.

## AI Collaboration
I used Claude Code throughout — for module structure, Gemini integration, test design, and debugging API errors. A genuinely useful suggestion was using a fact-checking scorer (score_response) instead of exact string assertions for AI output — that's actually how production AI evaluation works. One suggestion that was wrong: the initial SDK recommendation (google-generativeai) was fully deprecated; I caught it from the warning message and switched to google-genai myself.

## Biases and Limitations
The model has no actual pet care knowledge — it reasons over a schedule it didn't create. It assumes English, standard household pets, and won't flag obviously bad inputs like a 2-minute vet appointment. No memory between sessions, so it can't detect patterns over time. Prompt injection is possible since user input isn't sanitized before entering the prompt.

## Testing Results
- 13/13 unit tests passed (1 skipped due to Gemini 503, not a code issue)
- 4/4 evaluation scenarios passed
- Average confidence score: 1.00
- Live AI reliability test scored 1.0 on real Gemini output

## Reflection
This project reflects how I think about AI — not just throwing a model at a problem, but figuring out where it actually makes sense. Keeping the scheduler separate from the Gemini layer was a deliberate call because I wanted the core logic to stay predictable and testable, and let the AI do what it's actually good at: turning structured output into something readable. The reliability scorer came from realizing you can't just assert exact strings on LLM output the way you would with normal code. I also ran into real issues — a deprecated SDK, quota errors, a 503 mid-test — and figured them out without the answer being in any tutorial.

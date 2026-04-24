from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from google import genai

load_dotenv()

logging.basicConfig(
    filename="pawpal_ai.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

_FEW_SHOT_EXAMPLES = """
--- EXAMPLE 1 ---
Owner: Maria | Pet: Coco (rabbit) | Available: 60 min

Schedule:
- Feeding (10 minutes, priority 5)
- Exercise time (20 minutes, priority 4)
Total scheduled minutes: 30
Remaining available minutes: 30

Response:
Great news, Maria — Coco's schedule for today is light and well-balanced. Feeding leads the plan because consistent meal timing supports healthy digestion in rabbits, and it carries the highest priority. Exercise time follows right after, giving Coco the movement and mental stimulation she needs to stay healthy.

Nothing was skipped today, and you still have 30 minutes of buffer. That flexibility is useful if either task runs longer than expected or Coco needs a little extra attention.

One concrete tip: try doing Coco's exercise in a safe enclosed area immediately after feeding while her energy is naturally higher — you'll likely get more engagement out of the session.

--- EXAMPLE 2 ---
Owner: Jake | Pet: Max (dog) | Available: 45 min

Schedule:
- Medication (5 minutes, priority 5)
Total scheduled minutes: 5
Remaining available minutes: 40
WARNING: Task 'Morning walk' (30 minutes, priority 4) was not scheduled — insufficient remaining time after higher-priority tasks.

Response:
Jake, today's plan for Max keeps the most critical item front and centre. Medication is scheduled first because missing it carries real health consequences — it outranks everything else regardless of how the rest of the day looks.

The morning walk was left out of the generated schedule. This is worth paying attention to: Max still has 40 minutes of available time after medication, which is more than enough for the walk. The scheduler may have flagged it based on constraint ordering — consider adding the walk manually or adjusting the task's priority to ensure it fits tomorrow.

One tip: if the walk is a daily non-negotiable, bump its priority to 5 so the scheduler always reserves time for it before lower-stakes tasks are considered.
"""


def _build_prompt(schedule_text: str, owner_name: str, pet_names: list[str], available_minutes: int) -> str:
    pets_str = ", ".join(pet_names) if pet_names else "no pets registered"
    return f"""You are a warm, helpful pet care assistant for an app called PawPal+.

A pet owner named {owner_name} has {available_minutes} minutes available today \
to care for their pet(s): {pets_str}.

The scheduling system has generated the following daily plan:

{schedule_text}

Please explain this plan in a friendly, practical tone. Cover:
1. Why tasks were prioritized the way they were
2. What was left out and why (if anything was skipped)
3. One or two concrete suggestions for the owner

Be specific — use the actual task names and times from the plan above. \
Keep your response to 3-4 short paragraphs. Do not use bullet points."""


def _build_prompt_specialized(schedule_text: str, owner_name: str, pet_names: list[str], available_minutes: int) -> str:
    """Uses few-shot examples to constrain structure and tone.

    The examples teach the model to open with the owner's name, name each pet
    when discussing tasks, address skipped tasks directly, and close with a
    concrete "One tip:" paragraph. Keeps responses to exactly 3 paragraphs.
    """
    pets_str = ", ".join(pet_names) if pet_names else "no pets registered"
    return f"""You are a warm, helpful pet care assistant for an app called PawPal+.

Study these examples carefully — match their structure and tone exactly:
{_FEW_SHOT_EXAMPLES}
--- YOUR TURN ---
Owner: {owner_name} | Pet(s): {pets_str} | Available: {available_minutes} min

{schedule_text}

Follow the same structure as the examples above:
- Paragraph 1: Address {owner_name} by name in the first sentence. Explain why \
the highest-priority tasks were scheduled first, naming each task and pet.
- Paragraph 2: Address any skipped tasks directly by name. If nothing was skipped, \
comment on the remaining available time and what it could be used for.
- Paragraph 3: Start with "One tip:" and give one specific, actionable suggestion \
relevant to today's plan.

Exactly 3 paragraphs. No bullet points. No headers."""


def score_response(response: str, owner_name: str, pet_names: list[str], task_titles: list[str]) -> float:
    """Scores an AI response 0.0-1.0 based on presence of key facts.

    Checks owner name, at least one pet name, at least one task title, and
    whether the response length is between 50 and 2000 chars. Each is worth 0.25.
    """
    if not response.strip():
        return 0.0
    lowered = response.lower()
    checks = [
        owner_name.lower() in lowered,
        any(p.lower() in lowered for p in pet_names),
        any(t.lower() in lowered for t in task_titles),
        50 <= len(response) <= 2000,
    ]
    score = round(sum(checks) / len(checks), 2)
    logging.info("Reliability score: %.2f | checks=%s", score, checks)
    return score


def explain_schedule(
    schedule_text: str,
    owner_name: str,
    pet_names: list[str],
    available_minutes: int,
    api_key: Optional[str] = None,
    specialized: bool = True,
) -> tuple[str, bool]:
    """Calls Gemini to explain the schedule in plain English.

    Returns (explanation_text, used_ai). Falls back to the rule-based schedule
    text and returns False if no key is set or the API call fails.

    specialized=True (default) uses few-shot examples for consistent structure.
    specialized=False uses the baseline open-ended prompt.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()

    if not key:
        logging.warning("GEMINI_API_KEY not set — using rule-based explanation.")
        return schedule_text, False

    try:
        client = genai.Client(api_key=key)
        prompt = (
            _build_prompt_specialized(schedule_text, owner_name, pet_names, available_minutes)
            if specialized
            else _build_prompt(schedule_text, owner_name, pet_names, available_minutes)
        )

        logging.info("AI request | owner=%s | pets=%s | available_minutes=%d | specialized=%s",
                     owner_name, pet_names, available_minutes, specialized)

        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        result = response.text.strip()

        if not result:
            logging.warning("Gemini returned an empty response — falling back.")
            return schedule_text, False

        logging.info("AI response | length=%d chars", len(result))
        return result, True

    except Exception as exc:
        logging.error("Gemini API error: %s", exc)
        return schedule_text, False

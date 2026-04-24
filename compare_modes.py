from __future__ import annotations

import time
from datetime import date, datetime

from dotenv import load_dotenv
load_dotenv()

from ai_assistant import explain_schedule, score_response
from pawpal_system import Owner, Pet, Scheduler, Task

today = date.today()

owner = Owner(name="Jordan", available_minutes_per_day=90)
pet = Pet(name="Mochi", species="cat")
pet.add_task(Task(id="t1", title="Medication", duration_minutes=10, priority=5,
                  due_time=datetime.combine(today, datetime.min.time()).replace(hour=8)))
pet.add_task(Task(id="t2", title="Morning walk", duration_minutes=30, priority=5))
pet.add_task(Task(id="t3", title="Grooming", duration_minutes=60, priority=3))
owner.add_pet(pet)

scheduler = Scheduler(owner)
scheduler.generate_daily_plan(today)
schedule_text = scheduler.explain_plan()

TASK_TITLES = ["Medication", "Morning walk", "Grooming"]
PET_NAMES   = ["Mochi"]
OWNER_NAME  = "Jordan"


def analyse(text: str) -> dict:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return {
        "paragraphs":         len(paragraphs),
        "words":              len(text.split()),
        "opens_with_name":    OWNER_NAME.lower() in paragraphs[0].lower() if paragraphs else False,
        "mentions_pet":       any(p.lower() in text.lower() for p in PET_NAMES),
        "mentions_all_tasks": all(t.lower() in text.lower() for t in TASK_TITLES),
        "ends_with_tip":      any(
            paragraphs[-1].lower().startswith(kw)
            for kw in ("one tip", "tip:", "one concrete tip")
        ) if paragraphs else False,
        "score":              score_response(text, OWNER_NAME, PET_NAMES, TASK_TITLES),
    }


def divider(label: str = "") -> None:
    width = 64
    if label:
        pad = (width - len(label) - 2) // 2
        print("─" * pad + f" {label} " + "─" * pad)
    else:
        print("─" * width)


print("\n" + "=" * 64)
print("  PawPal+ Prompt Mode Comparison")
print("=" * 64)
print(f"\n  Schedule input:\n")
for line in schedule_text.strip().splitlines():
    print(f"    {line}")

print("\n")
divider("BASELINE MODE  (no few-shot examples)")
print()
baseline_text, b_ok = explain_schedule(schedule_text, OWNER_NAME, PET_NAMES, 90, specialized=False)
print(baseline_text if b_ok else "(API unavailable)")

print()
print(f"  Waiting 15s for rate limit...")
time.sleep(15)

print()
divider("SPECIALIZED MODE  (few-shot examples)")
print()
specialized_text, s_ok = explain_schedule(schedule_text, OWNER_NAME, PET_NAMES, 90, specialized=True)
print(specialized_text if s_ok else "(API unavailable)")

print()
divider("MEASURABLE DIFFERENCES")
print()

if b_ok and s_ok:
    b = analyse(baseline_text)
    s = analyse(specialized_text)

    metrics = [
        ("Paragraphs",            b["paragraphs"],         s["paragraphs"]),
        ("Word count",            b["words"],              s["words"]),
        ("Opens with owner name", b["opens_with_name"],    s["opens_with_name"]),
        ("Mentions pet name",     b["mentions_pet"],       s["mentions_pet"]),
        ("Mentions all tasks",    b["mentions_all_tasks"], s["mentions_all_tasks"]),
        ("Closes with tip",       b["ends_with_tip"],      s["ends_with_tip"]),
        ("Reliability score",     b["score"],              s["score"]),
    ]

    print(f"  {'Metric':<28} {'Baseline':>12}  {'Specialized':>12}")
    print("  " + "─" * 56)
    for label, bval, sval in metrics:
        changed = " ◄" if bval != sval else ""
        print(f"  {label:<28} {str(bval):>12}  {str(sval):>12}{changed}")

    print()
    print(f"  {sum(1 for _, bv, sv in metrics if bv != sv)} metric(s) changed between modes.")
else:
    print("  One or both API calls failed — check pawpal_ai.log.")

print("\n" + "=" * 64 + "\n")

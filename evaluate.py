from __future__ import annotations

import os
import time
from datetime import date, datetime

from dotenv import load_dotenv
load_dotenv()

from ai_assistant import explain_schedule, score_response
from pawpal_system import Owner, Pet, Scheduler, Task

PASS_THRESHOLD = 0.75
today = date.today()


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(today, datetime.min.time()).replace(hour=hour, minute=minute)


def scenario_standard() -> tuple[Owner, list[str], list[str]]:
    owner = Owner(name="Jordan", available_minutes_per_day=90)
    pet = Pet(name="Mochi", species="cat")
    pet.add_task(Task(id="s1", title="Medication", duration_minutes=10, priority=5, due_time=dt(8)))
    pet.add_task(Task(id="s2", title="Morning walk", duration_minutes=30, priority=5))
    pet.add_task(Task(id="s3", title="Grooming", duration_minutes=20, priority=3))
    owner.add_pet(pet)
    return owner, ["Mochi"], ["Medication", "Morning walk", "Grooming"]


def scenario_overloaded() -> tuple[Owner, list[str], list[str]]:
    owner = Owner(name="Alex", available_minutes_per_day=40)
    pet = Pet(name="Fido", species="dog")
    pet.add_task(Task(id="o1", title="Vet appointment", duration_minutes=30, priority=5, due_time=dt(10)))
    pet.add_task(Task(id="o2", title="Training session", duration_minutes=30, priority=4))
    pet.add_task(Task(id="o3", title="Evening walk", duration_minutes=20, priority=3))
    owner.add_pet(pet)
    return owner, ["Fido"], ["Vet appointment", "Training session", "Evening walk"]


def scenario_conflict() -> tuple[Owner, list[str], list[str]]:
    owner = Owner(name="Sam", available_minutes_per_day=120)
    pet = Pet(name="Biscuit", species="dog")
    pet.add_task(Task(id="c1", title="Breakfast", duration_minutes=30, priority=4, due_time=dt(8)))
    pet.add_task(Task(id="c2", title="Bath time", duration_minutes=45, priority=4, due_time=dt(8, 15)))
    owner.add_pet(pet)
    return owner, ["Biscuit"], ["Breakfast", "Bath time"]


def scenario_multi_pet() -> tuple[Owner, list[str], list[str]]:
    owner = Owner(name="Riley", available_minutes_per_day=120)
    cat = Pet(name="Luna", species="cat")
    cat.add_task(Task(id="m1", title="Feeding", duration_minutes=10, priority=5,
                      is_recurring=True, recurrence_rule="daily"))
    cat.add_task(Task(id="m2", title="Litter cleaning", duration_minutes=15, priority=4))
    dog = Pet(name="Biscuit", species="dog")
    dog.add_task(Task(id="m3", title="Morning walk", duration_minutes=30, priority=5,
                      is_recurring=True, recurrence_rule="daily"))
    dog.add_task(Task(id="m4", title="Training", duration_minutes=20, priority=3))
    owner.add_pet(cat)
    owner.add_pet(dog)
    return owner, ["Luna", "Biscuit"], ["Feeding", "Litter cleaning", "Morning walk", "Training"]


SCENARIOS = [
    ("Standard plan",         scenario_standard),
    ("Overloaded schedule",   scenario_overloaded),
    ("Time conflict",         scenario_conflict),
    ("Multi-pet / recurring", scenario_multi_pet),
]


def run_scenario(name: str, build_fn) -> dict:
    owner, pet_names, task_titles = build_fn()
    scheduler = Scheduler(owner)
    scheduler.generate_daily_plan(today)
    scheduled = scheduler.get_schedule()
    conflicts = scheduler.detect_conflicts(scheduled)
    rule_text = scheduler.explain_plan()

    ai_text, used_ai = explain_schedule(
        schedule_text=rule_text,
        owner_name=owner.name,
        pet_names=pet_names,
        available_minutes=owner.available_minutes_per_day,
    )

    score = score_response(ai_text, owner.name, pet_names, task_titles)
    return {
        "name": name,
        "tasks_scheduled": len(scheduled),
        "tasks_total": sum(len(p.tasks) for p in owner.pets),
        "conflicts": len(conflicts),
        "used_ai": used_ai,
        "score": score,
        "passed": score >= PASS_THRESHOLD,
    }


def main():
    print("\n" + "=" * 62)
    print("  PawPal+ AI Evaluation Harness")
    print("=" * 62)

    has_key = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    delay = 15 if has_key else 0  # free tier limit is 5 req/min

    results = []
    for i, (name, fn) in enumerate(SCENARIOS):
        print(f"\n  Running: {name}...")
        results.append(run_scenario(name, fn))
        if has_key and i < len(SCENARIOS) - 1:
            print(f"  (waiting {delay}s for rate limit...)")
            time.sleep(delay)

    print("\n" + "=" * 62)
    print(f"  {'Scenario':<26} {'Sched':>5}  {'Conf':>5}  {'AI':>5}  {'Pass':>5}")
    print("-" * 62)

    for r in results:
        print(f"  {r['name']:<26} {r['tasks_scheduled']}/{r['tasks_total']:>3}  "
              f"{r['score']:.2f}  {'yes' if r['used_ai'] else 'no':>5}  "
              f"{'PASS' if r['passed'] else 'FAIL':>5}")

    passed  = sum(1 for r in results if r["passed"])
    total   = len(results)
    avg     = sum(r["score"] for r in results) / total
    used_ai = sum(1 for r in results if r["used_ai"])

    if not has_key:
        ai_status = "no API key — fallback active"
    elif used_ai == total:
        ai_status = "all live Gemini responses"
    elif used_ai == 0:
        ai_status = "API errors on all calls — check pawpal_ai.log"
    else:
        ai_status = f"partial — {total - used_ai} call(s) fell back (check pawpal_ai.log)"

    print("-" * 62)
    print(f"  Result : {passed}/{total} passed")
    print(f"  Avg confidence score : {avg:.2f}")
    print(f"  AI used  : {used_ai}/{total} scenarios  ({ai_status})")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()

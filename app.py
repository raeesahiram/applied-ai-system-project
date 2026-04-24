import os
from datetime import date, datetime

import streamlit as st
from dotenv import load_dotenv

from ai_assistant import explain_schedule
from pawpal_system import Owner, Pet, Scheduler, Task

load_dotenv()

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("AI-powered pet care scheduling")

# ── Owner initialisation (must happen before sidebar reads owner.name) ─────────

if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes_per_day=120)

owner: Owner = st.session_state.owner

# ── Sidebar: owner settings ────────────────────────────────────────────────────

with st.sidebar:
    st.header("Owner Settings")
    owner_name_input = st.text_input("Your name", value=owner.name)
    available_minutes_input = st.number_input(
        "Minutes available today",
        min_value=10,
        max_value=480,
        value=owner.available_minutes_per_day,
        step=10,
    )

    if st.button("Update owner"):
        owner.name = owner_name_input
        owner.update_availability(int(available_minutes_input))
        st.success("Owner updated.")
        st.rerun()

# ── Pets ───────────────────────────────────────────────────────────────────────

st.subheader("Pets")

SPECIES_OPTIONS = ["Dog", "Cat", "Rabbit", "Bird", "Fish", "Hamster", "Guinea pig", "Reptile", "Other"]

with st.expander("Add a pet", expanded=not owner.pets):
    pet_name_input = st.text_input("Pet name", value="")
    species_choice = st.selectbox("Species", SPECIES_OPTIONS)
    if species_choice == "Other":
        species_input = st.text_input("Specify species", placeholder="e.g. turtle, ferret…")
    else:
        species_input = species_choice.lower()
    breed_input = st.text_input("Breed (optional)", value="")
    age_input = st.number_input("Age (years)", min_value=0, max_value=30, value=1)

    if st.button("Add pet"):
        name = pet_name_input.strip()
        if not name:
            st.error("Pet name cannot be empty.")
        elif any(p.name.lower() == name.lower() for p in owner.pets):
            st.error(f"A pet named '{name}' already exists.")
        elif not species_input.strip():
            st.error("Please specify a species.")
        else:
            new_pet = Pet(
                name=name,
                species=species_input.strip(),
                breed=breed_input.strip() or None,
                age=int(age_input),
            )
            owner.add_pet(new_pet)
            st.success(f"Added {new_pet.name}!")
            st.rerun()

if owner.pets:
    st.table(
        [
            {
                "Name": p.name,
                "Species": p.species,
                "Breed": p.breed or "—",
                "Age": p.age,
                "Tasks": len(p.tasks),
            }
            for p in owner.pets
        ]
    )

    with st.expander("Remove a pet"):
        pet_to_remove = st.selectbox(
            "Select pet to remove",
            [p.name for p in owner.pets],
            key="remove_pet_select",
        )
        st.caption("This will also remove all tasks assigned to that pet.")
        if st.button("Remove pet", type="secondary", key="remove_pet_btn"):
            owner.remove_pet(pet_to_remove)
            st.success(f"Removed {pet_to_remove}.")
            st.rerun()
else:
    st.info("No pets yet. Add one above.")

# ── Tasks ──────────────────────────────────────────────────────────────────────

st.subheader("Tasks")

if not owner.pets:
    st.warning("Add a pet before adding tasks.")
else:
    with st.expander("Add a task"):
        pet_selection = st.selectbox("Assign to pet", [p.name for p in owner.pets])
        task_title_input = st.text_input("Task title", value="")
        duration_input = st.number_input("Duration (minutes)", min_value=1, max_value=480, value=20)
        priority_input = st.select_slider(
            "Priority", options=[1, 2, 3, 4, 5], value=3,
            help="1 = low priority, 5 = high priority"
        )
        is_recurring_input = st.checkbox("Recurring daily?")

        if st.button("Add task"):
            title = task_title_input.strip()
            selected_pet = next(p for p in owner.pets if p.name == pet_selection)
            if not title:
                st.error("Task title cannot be empty.")
            elif any(t.title.lower() == title.lower() for t in selected_pet.tasks):
                st.error(f"'{title}' already exists for {selected_pet.name}.")
            else:
                new_task = Task(
                    id=f"{pet_selection}-{len(selected_pet.tasks) + 1}",
                    title=title,
                    duration_minutes=int(duration_input),
                    priority=int(priority_input),
                    is_recurring=is_recurring_input,
                    recurrence_rule="daily" if is_recurring_input else None,
                )
                selected_pet.add_task(new_task)
                st.success(f"Added '{new_task.title}' to {selected_pet.name}.")
                st.rerun()

    for pet in owner.pets:
        st.write(f"**{pet.name}**")
        if not pet.tasks:
            st.info(f"{pet.name} has no tasks yet.")
            continue

        st.table(
            [
                {
                    "Title": t.title,
                    "Duration (min)": t.duration_minutes,
                    "Priority": t.priority,
                    "Recurring": "Yes" if t.is_recurring else "No",
                    "Done": "✓" if t.completed else "—",
                }
                for t in pet.tasks
            ]
        )

        pending_tasks = [t for t in pet.tasks if not t.completed]
        col1, col2 = st.columns(2)

        with col1:
            if pending_tasks:
                task_to_complete = st.selectbox(
                    "Mark as done",
                    pending_tasks,
                    format_func=lambda t: t.title,
                    key=f"complete_select_{pet.name}",
                )
                if st.button("Mark done ✓", key=f"complete_btn_{pet.name}"):
                    next_task = task_to_complete.mark_completed()
                    if next_task:
                        pet.add_task(next_task)
                        st.success(f"Done! Next occurrence added.")
                    else:
                        st.success(f"Marked '{task_to_complete.title}' complete.")
                    st.rerun()

        with col2:
            task_to_remove = st.selectbox(
                "Remove task",
                pet.tasks,
                format_func=lambda t: t.title,
                key=f"remove_task_select_{pet.name}",
            )
            if st.button("Remove task ✕", key=f"remove_task_btn_{pet.name}", type="secondary"):
                pet.remove_task(task_to_remove.id)
                st.success(f"Removed '{task_to_remove.title}'.")
                st.rerun()

# ── Generate schedule ──────────────────────────────────────────────────────────

st.divider()
st.subheader("Generate Today's Schedule")

if st.button("Generate schedule", type="primary"):
    if not owner.pets:
        st.warning("Add at least one pet before generating a schedule.")
    elif not any(pet.tasks for pet in owner.pets):
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = Scheduler(owner)
        scheduler.generate_daily_plan(date.today())
        scheduled = scheduler.get_schedule()

        st.write("### Today's Schedule")

        conflicts = scheduler.detect_conflicts(scheduled)
        if conflicts:
            for warning_text in conflicts:
                st.warning(warning_text)

        if scheduled:
            st.table(
                [
                    {
                        "Task": task.title,
                        "Pet": next(
                            (p.name for p in owner.pets if task in p.tasks), "—"
                        ),
                        "Duration (min)": task.duration_minutes,
                        "Priority": task.priority,
                        "Due": task.due_time.strftime("%H:%M") if task.due_time else "—",
                    }
                    for task in scheduled
                ]
            )
        else:
            st.info("No tasks fit within today's available time.")

        # ── AI explanation ─────────────────────────────────────────────────────

        st.write("### AI Assistant")

        rule_based_text = scheduler.explain_plan()
        pet_names = [p.name for p in owner.pets]

        with st.spinner("Asking the AI assistant to explain your schedule…"):
            ai_text, used_ai = explain_schedule(
                schedule_text=rule_based_text,
                owner_name=owner.name,
                pet_names=pet_names,
                available_minutes=owner.available_minutes_per_day,
            )

        if used_ai:
            st.success("AI explanation ready.")
            st.write(ai_text)
        else:
            st.info(
                "No Gemini API key found — showing the rule-based explanation. "
                "Set GEMINI_API_KEY in a .env file to enable AI explanations."
            )
            st.text(ai_text)

        with st.expander("Raw scheduler output"):
            st.text(rule_based_text)

        # ── Pending tasks ──────────────────────────────────────────────────────

        pending = owner.get_tasks(completed=False)
        if pending:
            sorted_pending = sorted(
                pending,
                key=lambda t: t.due_time if t.due_time is not None else datetime.max,
            )
            with st.expander("All pending tasks (sorted by due time)"):
                st.table(
                    [
                        {
                            "Task": t.title,
                            "Pet": next(
                                (p.name for p in owner.pets if t in p.tasks), "—"
                            ),
                            "Due": t.due_time.strftime("%H:%M") if t.due_time else "—",
                            "Priority": t.priority,
                        }
                        for t in sorted_pending
                    ]
                )

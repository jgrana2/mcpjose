#!/usr/bin/env bash

# En lugar de esto:
# opencode --prompt "$execute_prompt"

# Esto:
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
PLAN_DIR="$SCRIPT_DIR/Plan"
ATOMIC_TASKS_FILE="$PLAN_DIR/AtomicTasks.json"

mode="${1:-}"
task_id=""

if [[ "$mode" != "--until-done" ]]; then
  task_id="$mode"
fi

outputs_dir="$SCRIPT_DIR/outputs"
mkdir -p "$outputs_dir"

ensure_plan_exists() {
  if [[ -f "$ATOMIC_TASKS_FILE" ]]; then
    return 0
  fi

  echo "No execution plan found in $PLAN_DIR."
  read -r -p "Enter the task to decompose and execute: " user_request

  if [[ -z "$user_request" ]]; then
    echo "A task description is required to generate the plan."
    exit 1
  fi

  mkdir -p "$PLAN_DIR"

  plan_prompt=$(cat <<EOF
You are working inside $SCRIPT_DIR.

Use the following decomposition framework exactly and generate the required JSON planning files in $PLAN_DIR.
Do not execute any atomic tasks yet. Only create the plan artifacts.

Framework:
$(cat "$SCRIPT_DIR/decomposition.md")

User request:
$user_request
EOF
)

  echo "Generating execution plan..."
  opencode run "$plan_prompt" || exit $?

  if [[ ! -f "$ATOMIC_TASKS_FILE" ]]; then
    echo "Plan generation did not produce $ATOMIC_TASKS_FILE."
    exit 1
  fi
}

get_first_pending_task_id() {
  PLAN_DIR="$PLAN_DIR" OUTPUTS_DIR="$outputs_dir" python3 - <<'PY'
import json
import os

plan_dir = os.environ["PLAN_DIR"]
outputs_dir = os.environ["OUTPUTS_DIR"]

with open(os.path.join(plan_dir, "AtomicTasks.json"), encoding="utf-8") as f:
    tasks = json.load(f)

for t in tasks["atomic_tasks"]:
    out_file = os.path.join(outputs_dir, f"{t['task_id']}.json")
    if not os.path.exists(out_file):
        print(t["task_id"])
        break
PY
}

ensure_plan_exists

if [[ "$mode" == "--until-done" ]]; then
  while true; do
    current_task_id="$(get_first_pending_task_id)"
    if [[ -z "$current_task_id" ]]; then
      echo "All tasks completed."
      exit 0
    fi

    echo "Running next pending task: $current_task_id"
    "$0" "$current_task_id" || exit $?
  done
fi

if [[ -z "$task_id" ]]; then
  task_id="$(get_first_pending_task_id)"
fi

if [[ -z "$task_id" ]]; then
  echo "No pending atomic tasks found."
  exit 0
fi

task_json=$(PLAN_DIR="$PLAN_DIR" TASK_ID="$task_id" python3 - <<'PY'
import json
import os

plan_dir = os.environ["PLAN_DIR"]
task_id = os.environ["TASK_ID"]

with open(os.path.join(plan_dir, "AtomicTasks.json"), encoding="utf-8") as f:
  tasks = json.load(f)

t = next(t for t in tasks["atomic_tasks"] if t["task_id"] == task_id)
print(json.dumps(t, indent=2))
PY
)

task_prompt="You are working inside $SCRIPT_DIR.

Execute this single atomic task only. Do not proceed to other tasks.

Task:
$task_json

Previous outputs available in: $outputs_dir

Instructions:
- Produce the actual deliverable of this task (files, code, data) directly in $SCRIPT_DIR.
- The deliverable location and format are defined in the task's exact_outputs field.
- After completing the task, save a completion record to $outputs_dir/${task_id}.json with:
  {
    \"task_id\": \"$task_id\",
    \"status\": \"completed\",
    \"outputs_produced\": [list of files created],
    \"notes\": \"any relevant observations\"
  }"

echo "Executing task: $task_id"
opencode run "$task_prompt"

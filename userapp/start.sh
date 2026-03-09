#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PLAN_DIR="$SCRIPT_DIR/Plan"

cd "$SCRIPT_DIR"

if ! command -v opencode >/dev/null 2>&1; then
  echo "Error: 'opencode' is not installed or not on PATH." >&2
  exit 1
fi

main_task="${*:-}"

if [[ -z "$main_task" ]]; then
  read -r -p "Enter the main task to decompose: " main_task
fi

if [[ -z "${main_task// }" ]]; then
  echo "Error: task cannot be empty." >&2
  exit 1
fi

mkdir -p "$PLAN_DIR"

required_plan_files=(
  "$PLAN_DIR/ReasoningChain.json"
  "$PLAN_DIR/FinalArtifactSpec.json"
  "$PLAN_DIR/DataSources.json"
  "$PLAN_DIR/DataSchema.json"
  "$PLAN_DIR/ExecutionPlan.json"
  "$PLAN_DIR/ValidationRules.json"
  "$PLAN_DIR/TaskTree.json"
  "$PLAN_DIR/AtomicTasks.json"
)

read -r -d '' decompose_prompt <<EOF_PROMPT || true
You are working inside the git repository at $SCRIPT_DIR.

Read $SCRIPT_DIR/decomposition.md and decompose this task into the required planning artifacts:

$main_task

Requirements:
- Follow decomposition.md exactly.
- Create or overwrite all required JSON files in $PLAN_DIR.
- Produce only the planning artifacts; do not execute the plan yet.
- Ensure every JSON file is valid and internally consistent.
- Briefly confirm which files were created at the end.
EOF_PROMPT

opencode run "$decompose_prompt"

for file in "${required_plan_files[@]}"; do
  if [[ ! -s "$file" ]]; then
    echo "Error: required plan artifact missing or empty: $file" >&2
    exit 1
  fi
  python3 -m json.tool "$file" >/dev/null
done

read -r -d '' execute_prompt <<EOF_PROMPT || true
You are working inside the git repository at $SCRIPT_DIR.

Execute the task using the plan artifacts in $PLAN_DIR.

Task:
$main_task

Execution requirements:
- Read and follow ReasoningChain.json, FinalArtifactSpec.json, DataSources.json, DataSchema.json, ExecutionPlan.json, ValidationRules.json, TaskTree.json, and AtomicTasks.json.
- Execute the plan in dependency order.
- Use the planning artifacts as constraints during implementation.
- Validate the work against the defined quality gates before finishing.
- If you must ask for clarification, use a multiple choice format.
EOF_PROMPT

opencode --prompt "$execute_prompt"

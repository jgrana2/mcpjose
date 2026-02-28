#!/bin/bash

# Ask user input for the main task to decompose
read -p "Enter the main task to decompose: " main_task

# Run the OpenCode command to follow decomposition.md based on main_task
opencode run "Decompose the main task '$main_task' into smaller sub-tasks according to the guidelines in decomposition.md."

# Run the OpenCode command to execute the plan in Plan/ExecutionPlan.json - this works great
opencode run "Implement the plan in Plan/ExecutionPlan.json. Use all skills and tools available to you. If you need to ask me questions to clarify the implementation plan or make a decision, ask them in a multiple choice format."

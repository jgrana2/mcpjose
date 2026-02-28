#!/bin/bash

opencode run "Execute the workflow defined in Prompts/PromptIndex.json. Find the next node with status != 'passed' according to execution_order, load its prompt file, execute it, update the node's status to 'passed', and repeat until all nodes are completed or the context window is full."

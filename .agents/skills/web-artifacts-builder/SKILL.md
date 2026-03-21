---
name: web-artifacts-builder
description: Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state management, routing, or shadcn/ui components - not for simple single-file HTML/JSX artifacts.
license: Complete terms in LICENSE.txt
---

# Web Artifacts Builder

To build powerful frontend claude.ai artifacts, follow these steps:
1. Initialize the frontend repo using standard filesystem tools (`write`/`create_directory`).
2. Develop your artifact by editing the generated code.
3. Use the `web-artifacts-builder` tool to bundle your code into a single HTML artifact.
4. Display artifact to user.

**Stack**: React 18 + TypeScript + Vite + Parcel (bundling) + Tailwind CSS + shadcn/ui

## Design & Style Guidelines

VERY IMPORTANT: To avoid what is often referred to as "AI slop", avoid using excessive centered layouts, purple gradients, uniform rounded corners, and Inter font.

## Quick Start

### Step 1: Initialize Project

Create a new React project manually using standard tools:
```bash
mkdir <project-name>
cd <project-name>
# Create project files (package.json, src/App.tsx, etc.) using `write`
```

### Step 2: Develop Your Artifact

To build the artifact, edit the generated files using the `edit` or `write` tools.

### Step 3: Bundle to Single HTML File

Use the `web-artifacts-builder` tool to create `bundle.html` - a self-contained artifact with all JavaScript, CSS, and dependencies inlined. This file can be directly shared in Claude conversations as an artifact.

### Step 4: Share Artifact with User

Finally, share the bundled HTML file in conversation with the user so they can view it as an artifact.

## Reference

- **shadcn/ui components**: https://ui.shadcn.com/docs/components
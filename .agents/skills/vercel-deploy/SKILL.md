---
name: vercel-deploy
description: Deploy applications and websites to Vercel. Use when the user requests deployment actions like "deploy my app", "deploy and give me the link", "push this live", or "create a preview deployment".
---

# Vercel Deploy

Deploy any project to Vercel instantly. **Always deploy as preview** (not production) unless the user explicitly asks for production.

## Prerequisites

- Ensure the Vercel CLI is installed (`command -v vercel`).
- Deployment might take a few minutes. Use appropriate timeout values.

## Quick Start

1. Deploy the current directory (or a specified path):
   ```bash
   vercel deploy [path] --yes
   ```

**Important:** Use a 10-minute (600000ms) timeout for the deploy command, as builds can take significant time.

## Production Deploys

Only if the user explicitly asks:
```bash
vercel deploy [path] --prod --yes
```

## Output

Show the user the deployment URL provided by the Vercel CLI output.

**Do not** curl or fetch the deployed URL to verify it works. Just return the link.


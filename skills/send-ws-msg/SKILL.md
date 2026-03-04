---
name: send-ws-msg
description: Use the `send_ws_msg` MCP tool to send WhatsApp messages via Meta WhatsApp Cloud API, with allowlisting and a daily send cap.
---

# send-ws-msg

## What this skill covers

How to use this repo’s MCP tool `send_ws_msg` (WhatsApp Cloud API), including configuration, allowlisting, and the daily cap.

## Prereqs (Meta WhatsApp Cloud API)

You need a WhatsApp Business Platform setup in Meta:
- A WhatsApp-enabled phone number in WhatsApp Manager
- A Phone Number ID
- An access token with permission to send messages

## Configuration

Set these env vars (recommended: `auth/.env` or `auth/credentials.json`):

- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_API_VERSION` (optional, default `v21.0`)

Destination controls:
- `WHATSAPP_DEFAULT_DESTINATION` (required as fallback; used when no destination is provided)

Daily cap:
- `WHATSAPP_DAILY_MAX` (default `10`, counted per local day)
- `WHATSAPP_TIMEZONE` (optional IANA timezone like `America/Los_Angeles`; defaults to system local timezone)
- `MCPJOSE_RATE_LIMIT_DB` (optional; default `auth/rate_limits.sqlite`)

## Tool usage

Tool: `send_ws_msg`
- Inputs:
  - `destination` (string | null): E.164-ish number. If provided, sends to this number. If null/empty, uses `WHATSAPP_DEFAULT_DESTINATION` as fallback.
  - `message` (string): message body
- Output:
  - `{ ok, destination, provider, message_id?, rate_limit?, error? }`

Examples:
```json
{ "destination": "+14155550123", "message": "Hi! This is a test." }
```
```json
{ "message": "Hi! This goes to default destination." }
```

## Troubleshooting

- `Missing destination`: provide a `destination` parameter or set `WHATSAPP_DEFAULT_DESTINATION`.
- `Daily rate limit exceeded`: increase `WHATSAPP_DAILY_MAX` or wait until the next UTC day.

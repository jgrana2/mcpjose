---
name: send-ws-msg
description: Use the `send_ws_msg` MCP tool to send WhatsApp messages via Meta WhatsApp Cloud API, with allowlisting, media support, and a daily cap.
---

# send-ws-msg

## What this skill covers

How to use this repo’s MCP tool `send_ws_msg` (WhatsApp Cloud API), including configuration, allowlisting, media delivery, and the daily cap.

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

### Inputs
- `destination` (string | null): E.164-ish number. If provided, sends to this number. If null/empty, uses `WHATSAPP_DEFAULT_DESTINATION` as fallback.
- `message` (string): required text body. For media messages, this becomes the caption.
- `template_name` (string | null): optional message template name.
- `language_code` (string | null): optional language for templates.
- `image_path` (string | null): local image file path to upload and send.
- `media_path` (string | null): local media file path to upload and send.
- `media_url` (string | null): public URL to an image to send.
- `mime_type` (string | null): optional MIME type override for uploads.

### Behavior
- If `image_path` or `media_path` is provided, the tool uploads the local file to WhatsApp Cloud API and sends it as an image message.
- If `media_url` is provided, the tool sends an image message using the URL.
- The `message` text is used as the image caption for media messages.
- Text-only behavior remains unchanged when no media is supplied.
- Do not provide both a local media path and `media_url` at the same time.

### Output
- `{ ok, destination, provider, message_id?, rate_limit?, error? }`

## Examples

Text only:
```json
{ "destination": "+14155550123", "message": "Hi! This is a test." }
```

Text to default destination:
```json
{ "message": "Hi! This goes to default destination." }
```

Upload and send a local image:
```json
{
  "destination": "+14155550123",
  "message": "Test image caption",
  "image_path": "/path/to/image.png"
}
```

Send an image by public URL:
```json
{
  "destination": "+14155550123",
  "message": "Test image caption",
  "media_url": "https://example.com/image.png"
}
```

## Troubleshooting

- `Missing destination`: provide a `destination` parameter or set `WHATSAPP_DEFAULT_DESTINATION`.
- `Daily rate limit exceeded`: increase `WHATSAPP_DAILY_MAX` or wait until the next local day.
- `Provide either a local media path or media_url, not both.`: choose one media source.
- `File not found`: verify the local media path exists.
- `WhatsApp media upload did not return an id`: check the upload response and Media API permissions.

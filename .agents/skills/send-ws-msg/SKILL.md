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
- `WHATSAPP_DAILY_MAX` (default `100`, counted per local day)
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

## Image Size Optimization

WhatsApp Cloud API has file size limits. Large images (especially high-resolution PNGs from AI generation) may fail with error #100 (Invalid parameter).

**Recommended workflow for sending generated images:**

1. Check image file size first: `ls -lh image.png`
2. If larger than ~500KB, resize and compress:
   ```bash
   # Resize to 30-50% and convert to JPEG with 80% quality
   magick image.png -resize 30% -quality 80 image.jpg
   ```
3. Send the optimized image with proper MIME type:
   ```json
   {
     "destination": "+573001234567",
     "message": "Here's the image!",
     "image_path": "image.jpg",
     "mime_type": "image/jpeg"
   }
   ```

**Best practices:**
- Resize large images to 1024px max dimension (WhatsApp will resize anyway)
- Convert PNG to JPEG for photos/artwork (smaller file size)
- Keep final image under 5MB (ideally under 500KB for faster upload)

## Troubleshooting

- `Missing destination`: provide a `destination` parameter or set `WHATSAPP_DEFAULT_DESTINATION`.
- `Daily rate limit exceeded`: increase `WHATSAPP_DAILY_MAX` or wait until the next local day.
- `Provide either a local media path or media_url, not both.`: choose one media source.

---

## Receiving Files & Media

When users send files, images, audio, or video to the WhatsApp number, the webhook stores them in the local SQLite database. The agent loop automatically processes incoming media:

- **Images** → analyzed via vision pipeline (OpenAI/Gemini)
- **Audio/Voice** → transcribed via Whisper
- **Documents** (PDF, DOCX, XLSX, TXT, CSV, etc.) → downloaded and content extracted where possible; file path provided to the agent for further tool-based processing
- **Video** → downloaded and file path provided to the agent

### Stored message fields

Messages from `get_ws_messages` now include:
- `media_id`: WhatsApp media ID (use with `download_ws_media` to download)
- `media_type`: one of `image`, `audio`, `video`, `document`
- `filename`: original filename (documents only)

### Tool: `download_ws_media`

Download any received WhatsApp media file by its `media_id`.

#### Inputs
- `media_id` (string, required): the WhatsApp media ID from a received message
- `output_dir` (string | null): optional local directory to save the file (defaults to temp dir)

#### Output
```json
{
  "ok": true,
  "media_id": "123456789",
  "file_path": "/tmp/whatsapp_123456789_report.pdf",
  "file_size_bytes": 204800
}
```

#### Workflow: Processing a received document
1. Call `get_ws_messages` to see recent messages
2. Find a message with `type: "document"` and note its `media_id` and `filename`
3. Call `download_ws_media` with the `media_id`
4. Use the returned `file_path` with other tools (read_file, google_ocr, bash_execute, etc.)

#### Example
```json
{ "media_id": "1234567890" }
```

```json
{ "media_id": "1234567890", "output_dir": "/tmp/downloads" }
```
- `File not found`: verify the local media path exists.
- `WhatsApp media upload did not return an id`: check the upload response and Media API permissions.
- `(#100) Invalid parameter`: image file may be too large. Resize/compress before sending (see Image Size Optimization section above).

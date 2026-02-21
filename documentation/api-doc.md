# API Documentation

## Base URL
`http://localhost:5000`

## Candidate APIs

### POST /candidates/upload
Upload and parse a resume (PDF/DOCX). Data is saved only when extraction succeeds.

- Content-Type: `multipart/form-data`
- Body: `resume` (file)

Success `201`:
```json
{
  "id": "uuid",
  "confidence": 0.95,
  "messages": [
    "Resume uploaded successfully",
    "Extraction successful",
    "Fields have been saved to DB"
  ]
}
```

Error examples:
- `400` invalid file input
- `422` extraction failure with reason
- `500` DB or server failure

### GET /candidates
List all candidates.

Success `200`:
```json
[
  {
    "id": "uuid",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "company": "Example Corp",
    "designation": "Engineering Lead",
    "skills": ["Python", "Flask"],
    "company_history": [
      {"company": "Example Corp", "duration": "2024 - Present", "is_current": true}
    ],
    "extraction_status": "Extracted",
    "confidence": 0.95,
    "telegram_username": "john_doe"
  }
]
```

### GET /candidates/<id>
Fetch full candidate profile.

- `200` candidate payload
- `404` not found

### DELETE /candidates/<id>
Permanently deletes candidate, related documents/requests, and stored files.

Success `200`:
```json
{"message":"Candidate profile and files deleted permanently"}
```

### POST /candidates/<id>/telegram
Update Telegram identity (username/phone/chat-id as your workflow requires).

Request:
```json
{"telegram_username":"john_doe"}
```

- `200` updated
- `400` missing value

### POST /candidates/<id>/request-documents
Triggers Mr Traqchecker over Telegram to start PAN/Aadhaar collection.

Success `200`:
```json
{
  "request_id": "uuid",
  "message": "Mr Traqchecker has initiated document collection on Telegram."
}
```

Possible errors:
- `404` candidate not found
- `409` Telegram link required (candidate must `/start <phone_number>` once)
- `500` bot token misconfiguration
- `502` Telegram delivery/API failure

### GET /candidates/<id>/documents
List collected/uploaded documents.

Success `200`:
```json
[
  {"type":"PAN","path":"uploads/...","status":"collected"}
]
```

### POST /candidates/<id>/submit-documents
Manual web upload of PAN + Aadhaar from frontend.

- Content-Type: `multipart/form-data`
- Body: `pan` file, `aadhaar` file

## Telegram Webhook APIs

### POST /telegram/webhook
Telegram webhook receiver endpoint.

- Validates `X-Telegram-Bot-Api-Secret-Token` when `TELEGRAM_WEBHOOK_SECRET` is configured.
- Processes candidate linking (`/start <phone_number>`) and PAN/Aadhaar collection conversation.

### POST /telegram/setup-webhook
Registers Telegram webhook URL using `PUBLIC_BASE_URL`.

Success `200`:
```json
{
  "message": "Telegram webhook configured",
  "webhook_url": "https://<public-base>/telegram/webhook"
}
```

### GET /telegram/webhook-info
Returns Telegram webhook status from Bot API.

## Suggested Setup Sequence

1. Configure `.env` with `TELEGRAM_API_TOKEN` (or `TELEGRAM_API_KEY`) and `PUBLIC_BASE_URL`.
2. Start backend.
3. Call:
```bash
curl -X POST http://127.0.0.1:5000/telegram/setup-webhook
```
4. Verify:
```bash
curl http://127.0.0.1:5000/telegram/webhook-info
```
5. Candidate sends `/start <phone_number_used_in_application>` to bot once.
6. Use frontend button `Ask Mr Traqchecker to Request Documents`.

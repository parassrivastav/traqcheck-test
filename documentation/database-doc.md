# Database Documentation

## Database
SQLite (`database.db`)

## Tables

### candidates
Stores extracted candidate profile data.

| Column | Type | Description |
|---|---|---|
| id | TEXT | Primary key (UUID) |
| name | TEXT | Candidate name |
| email | TEXT | Candidate email |
| phone | TEXT | Candidate phone number |
| company | TEXT | Current/latest company |
| designation | TEXT | Current/latest designation |
| skills | TEXT | JSON array of skills |
| company_history | TEXT | JSON array of company objects (`company`,`duration`,`is_current`) |
| resume_path | TEXT | Uploaded resume path |
| telegram_username | TEXT | Telegram identity value used by your workflow |

### documents
Stores PAN/Aadhaar documents submitted through web upload or Telegram webhook.

| Column | Type | Description |
|---|---|---|
| id | TEXT | Primary key (UUID) |
| candidate_id | TEXT | FK to candidates.id |
| type | TEXT | `PAN` or `Aadhaar` |
| path | TEXT | Stored file path |
| status | TEXT | `pending` or `collected` |

### requests
Document-request audit records.

| Column | Type | Description |
|---|---|---|
| id | TEXT | Primary key (UUID) |
| candidate_id | TEXT | FK to candidates.id |
| request_text | TEXT | Trigger text sent/generated |
| timestamp | TEXT | ISO timestamp |

### telegram_links
Maps candidate profile to Telegram chat.

| Column | Type | Description |
|---|---|---|
| candidate_id | TEXT | PK/FK to candidates.id |
| chat_id | TEXT | Telegram chat ID |
| telegram_identity | TEXT | Username/identity used during linking |
| updated_at | TEXT | ISO timestamp |

### telegram_sessions
Persists Mr Traqchecker conversation progress.

| Column | Type | Description |
|---|---|---|
| chat_id | TEXT | Primary key |
| candidate_id | TEXT | FK to candidates.id |
| stage | TEXT | `pan`, `aadhaar`, `done` |
| history | TEXT | Conversation transcript |
| updated_at | TEXT | ISO timestamp |

## Relationships
- `documents.candidate_id` -> `candidates.id`
- `requests.candidate_id` -> `candidates.id`
- `telegram_links.candidate_id` -> `candidates.id`
- `telegram_sessions.candidate_id` -> `candidates.id`

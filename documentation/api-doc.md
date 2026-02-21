# API Documentation

## Base URL
`http://localhost:5000`

## Endpoints

### 1. POST /candidates/upload
Upload a candidate's resume (PDF or DOCX).

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: `resume` (file)

**Sample Request:**
```
curl -X POST http://localhost:5000/candidates/upload \
  -F "resume=@resume.pdf"
```

**Response:**
- Status: 201 Created
- Body:
```json
{
  "id": "uuid",
  "message": "Resume uploaded successfully"
}
```

**Error Responses:**
- 400 Bad Request: No file part, No selected file, Invalid file type

### 2. GET /candidates
List all candidates.

**Request:**
- Method: GET

**Sample Request:**
```
curl -X GET http://localhost:5000/candidates
```

**Response:**
- Status: 200 OK
- Body: Array of candidates
```json
[
  {
    "id": "uuid",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "company": "Example Corp",
    "designation": "Software Engineer",
    "skills": ["Python", "Flask", "SQL"]
  }
]
```

### 3. GET /candidates/<id>
Get a candidate's parsed profile.

**Request:**
- Method: GET
- Path Parameter: `id` (string)

**Sample Request:**
```
curl -X GET http://localhost:5000/candidates/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
- Status: 200 OK
- Body:
```json
{
  "id": "uuid",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "company": "Example Corp",
  "designation": "Software Engineer",
  "skills": ["Python", "Flask", "SQL"]
}
```

**Error Responses:**
- 404 Not Found: Candidate not found

### 4. POST /candidates/<id>/request-documents
Generate and log a personalized request for PAN/Aadhaar documents.

**Request:**
- Method: POST
- Path Parameter: `id` (string)

**Sample Request:**
```
curl -X POST http://localhost:5000/candidates/123e4567-e89b-12d3-a456-426614174000/request-documents
```

**Response:**
- Status: 200 OK
- Body:
```json
{
  "request_id": "uuid",
  "message": "Dear John Doe, please provide your PAN and Aadhaar documents for verification."
}
```

**Error Responses:**
- 404 Not Found: Candidate not found

### 5. POST /candidates/<id>/submit-documents
Submit PAN and Aadhaar documents.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: `pan` (file), `aadhaar` (file)

**Sample Request:**
```
curl -X POST http://localhost:5000/candidates/123e4567-e89b-12d3-a456-426614174000/submit-documents \
  -F "pan=@pan.jpg" \
  -F "aadhaar=@aadhaar.jpg"
```

**Response:**
- Status: 200 OK
- Body:
```json
{
  "message": "Documents submitted successfully"
}
```

### 6. POST /candidates/<id>/telegram
Update candidate's Telegram username.

**Request:**
- Method: POST
- Path Parameter: `id` (string)
- Body: JSON
```json
{
  "telegram_username": "username"
}
```

**Sample Request:**
```
curl -X POST http://localhost:5000/candidates/123e4567-e89b-12d3-a456-426614174000/telegram \
  -H "Content-Type: application/json" \
  -d '{"telegram_username": "john_doe"}'
```

**Response:**
- Status: 200 OK
- Body:
```json
{
  "message": "Telegram username updated"
}
```

**Error Responses:**
- 400 Bad Request: telegram_username required
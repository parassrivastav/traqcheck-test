# TraqCheck Full-Stack Application

A full-stack candidate management system with Flask backend and React frontend for resume parsing and document verification.

## Features

### Backend (Flask)
- Resume upload and parsing (PDF/DOCX) with OpenAI
- Candidate profile management
- Mr Traqchecker-triggered document requests
- Document submission (PAN/Aadhaar)
- SQLite database
- RESTful API with CORS support
- Telegram webhook integration for document collection

### Frontend (React)
- Drag-and-drop resume upload with progress
- Candidate dashboard (table view)
- Candidate profile view with extracted data and confidence scores
- Document request generation
- Document upload and viewing
- Telegram username management
- Responsive UI with modern design

### AI Agent (LangChain + Telegram Webhook)
- Conversational Mr Traqchecker agent for natural language document collection
- Agenda-constrained conversation to collect PAN and Aadhaar
- Accepts image, PDF/document, or text inputs via Telegram
- Stores collected artifacts in `documents` table and `uploads/`

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and update the values (add your OpenAI and Telegram API keys)
3. Run `./setup.sh` to install backend/frontend dependencies
4. Configure `.env` values:
   - `OPENAI_API_KEY`
   - `TELEGRAM_API_TOKEN` (or `TELEGRAM_API_KEY`)
   - `PUBLIC_BASE_URL` (public URL that reaches your Flask server)
   - `TELEGRAM_WEBHOOK_SECRET` (optional but recommended)
5. Run `./startup.sh` to start frontend + backend. It attempts webhook setup automatically when env values are present.

## Usage

- **Frontend**: Access `http://localhost:3000` for the web interface
- **Backend API**: Available at `http://localhost:5000`
- **Telegram Webhook**: `/telegram/webhook` receives Telegram updates

## API Documentation

See `documentation/api-doc.md` for detailed API endpoints.

## Database Schema

See `documentation/database-doc.md` for database structure.

## Environment Variables

- `SECRET_KEY`: Flask secret key
- `DEBUG`: Enable debug mode (True/False)
- `DATABASE`: SQLite database file path
- `UPLOAD_FOLDER`: Folder for uploaded files
- `HOST`: Server host (default: 127.0.0.1)
- `PORT`: Server port (default: 5000)
- `OPENAI_API_KEY`: OpenAI API key for resume parsing
- `TELEGRAM_API_TOKEN`: Telegram bot API token
- `TELEGRAM_API_KEY`: Legacy fallback token name
- `PUBLIC_BASE_URL`: Public base URL for webhook registration
- `TELEGRAM_WEBHOOK_SECRET`: Optional Telegram webhook secret token

## Project Structure

```
traqcheck-test/
├── app.py                 # Flask backend application
├── resume_extractor.py    # OpenAI resume extraction logic
├── requirements.txt       # Python dependencies
├── setup.sh              # Setup script
├── startup.sh            # Startup script
├── .env                  # Environment variables
├── .gitignore            # Git ignore rules
├── database.db           # SQLite database
├── uploads/              # Uploaded files
├── documentation/        # API and database docs
└── frontend/             # React frontend
    ├── public/
    ├── src/
    ├── package.json
    └── ...
```

## Technologies Used

- **Backend**: Flask, SQLite, python-dotenv, flask-cors, OpenAI API, PyPDF2, python-docx
- **Frontend**: React, axios, react-dropzone
- **AI Agent**: LangChain, OpenAI, Telegram Bot API webhook
- **Deployment**: Development servers with hot reload

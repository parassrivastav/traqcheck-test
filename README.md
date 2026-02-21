# TraqCheck Full-Stack Application

A full-stack candidate management system with Flask backend and React frontend for resume parsing and document verification.

## Features

### Backend (Flask)
- Resume upload and parsing (PDF/DOCX) with OpenAI
- Candidate profile management
- AI-generated document requests
- Document submission (PAN/Aadhaar)
- SQLite database
- RESTful API with CORS support
- Telegram bot integration for document collection

### Frontend (React)
- Drag-and-drop resume upload with progress
- Candidate dashboard (table view)
- Candidate profile view with extracted data and confidence scores
- Document request generation
- Document upload and viewing
- Telegram username management
- Responsive UI with modern design

### AI Agent (LangChain + Telegram)
- Conversational AI agent for natural language document collection
- Iterative conversation to collect PAN and Aadhaar images
- Automatic image download and storage
- Integration with candidate database

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and update the values (add your OpenAI and Telegram API keys)
3. Run `./setup.sh` to install backend, frontend, and AI agent dependencies
4. Run `./startup.sh` to start the full application (backend, frontend, and Telegram bot)

## Usage

- **Frontend**: Access `http://localhost:3000` for the web interface
- **Backend API**: Available at `http://localhost:5000`
- **Telegram Bot**: Active and ready to handle document collection conversations

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
- `TELEGRAM_API_KEY`: Telegram bot API key for AI agent

## Project Structure

```
traqcheck-test/
├── app.py                 # Flask backend application
├── openai.py              # OpenAI resume extraction logic
├── telegram_bot.py        # Telegram bot with LangChain AI agent
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
- **AI Agent**: LangChain, python-telegram-bot, OpenAI
- **Deployment**: Development servers with hot reload
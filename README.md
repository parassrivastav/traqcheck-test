# TraqCheck Full-Stack Application

A full-stack candidate management system with Flask backend and React frontend for resume parsing and document verification.

## Features

### Backend (Flask)
- Resume upload and parsing (PDF/DOCX)
- Candidate profile management
- AI-generated document requests
- Document submission (PAN/Aadhaar)
- SQLite database
- RESTful API with CORS support

### Frontend (React)
- Drag-and-drop resume upload with progress
- Candidate dashboard (table view)
- Candidate profile view with extracted data and confidence scores
- Document request generation
- Document upload and viewing
- Responsive UI with modern design

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and update the values
3. Run `./setup.sh` to install backend and frontend dependencies
4. Run `./startup.sh` to start both backend and frontend servers

## Usage

- **Frontend**: Access `http://localhost:3000` for the web interface
- **Backend API**: Available at `http://localhost:5000`

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

## Project Structure

```
traqcheck-test/
├── app.py                 # Flask backend application
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
- **Deployment**: Development servers with hot reload
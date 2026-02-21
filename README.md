# TraqCheck Backend

A Flask-based backend for candidate management system with resume parsing and document verification.

## Features

- Resume upload and parsing (PDF/DOCX)
- Candidate profile management
- AI-generated document requests
- Document submission (PAN/Aadhaar)
- SQLite database

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and update the values
3. Run `./setup.sh` to install dependencies
4. Run `./startup.sh` to start the server

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
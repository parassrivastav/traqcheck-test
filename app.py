from flask import Flask, request, jsonify, send_from_directory
import os
import sqlite3
import json
from werkzeug.utils import secure_filename
import re
from datetime import datetime
import uuid
from dotenv import load_dotenv
from flask_cors import CORS
from resume_extractor import extract_resume_info, ResumeExtractionError

load_dotenv()

app = Flask(__name__)

CORS(app)  # Enable CORS for all routes

# Configuration from environment variables
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['DEBUG'] = os.environ.get('DEBUG', 'True').lower() == 'true'
DATABASE = os.environ.get('DATABASE', 'database.db')
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Backend Status</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                color: white;
            }
            .container {
                text-align: center;
                background: rgba(255, 255, 255, 0.1);
                padding: 50px;
                border-radius: 15px;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                backdrop-filter: blur(4px);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
            h1 {
                font-size: 3em;
                margin-bottom: 20px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            p {
                font-size: 1.2em;
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Backend Running</h1>
            <p>The TraqCheck backend is up and running successfully!</p>
        </div>
    </body>
    </html>
    """

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            company TEXT,
            designation TEXT,
            skills TEXT,
            company_history TEXT,
            resume_path TEXT,
            telegram_username TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            candidate_id TEXT,
            type TEXT,
            path TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS requests (
            id TEXT PRIMARY KEY,
            candidate_id TEXT,
            request_text TEXT,
            timestamp TEXT
        )''')

def ensure_candidate_columns():
    with get_db() as conn:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(candidates)").fetchall()
        }
        if "company_history" not in columns:
            conn.execute(
                "ALTER TABLE candidates ADD COLUMN company_history TEXT DEFAULT '[]'"
            )


init_db()
ensure_candidate_columns()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_resume_data(file_path, filename):
    # Extract data using OpenAI
    data = extract_resume_info(file_path)
    data['confidence'] = 0.95  # Add confidence score
    return data

@app.route('/candidates/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        try:
            data = extract_resume_data(file_path, filename)
        except ResumeExtractionError as exc:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({
                'error': f'Error parsing the resume because {exc}',
                'stage': 'extraction'
            }), 422
        except Exception as exc:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({
                'error': f'Error parsing the resume because {exc}',
                'stage': 'extraction'
            }), 500

        candidate_id = str(uuid.uuid4())

        try:
            with get_db() as conn:
                conn.execute('INSERT INTO candidates (id, name, email, phone, company, designation, skills, company_history, resume_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                             (candidate_id, data['name'], data['email'], data['phone'], data['company'], data['designation'], json.dumps(data['skills']), json.dumps(data.get('company_history', [])), file_path))
        except Exception as exc:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({
                'error': f'Error parsing the resume because DB save failed: {exc}',
                'stage': 'db_save'
            }), 500

        return jsonify({
            'id': candidate_id,
            'confidence': data['confidence'],
            'messages': [
                'Resume uploaded successfully',
                'Extraction successful',
                'Fields have been saved to DB'
            ]
        }), 201
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/candidates', methods=['GET'])
def list_candidates():
    with get_db() as conn:
        candidates = conn.execute('SELECT id, name, email, phone, company, designation, skills, company_history, telegram_username FROM candidates').fetchall()
    result = []
    for c in candidates:
        try:
            skills = json.loads(c['skills']) if c['skills'] else []
        except json.JSONDecodeError:
            skills = []
        try:
            company_history = json.loads(c['company_history']) if c['company_history'] else []
        except json.JSONDecodeError:
            company_history = []
        result.append({
            'id': c['id'],
            'name': c['name'],
            'email': c['email'],
            'phone': c['phone'],
            'company': c['company'],
            'designation': c['designation'],
            'skills': skills,
            'company_history': company_history,
            'extraction_status': 'Extracted',
            'confidence': 0.95,
            'telegram_username': c['telegram_username']
        })
    return jsonify(result)

@app.route('/candidates/<id>', methods=['GET'])
def get_candidate(id):
    with get_db() as conn:
        candidate = conn.execute('SELECT * FROM candidates WHERE id = ?', (id,)).fetchone()
    if candidate:
        try:
            skills = json.loads(candidate['skills']) if candidate['skills'] else []
        except json.JSONDecodeError:
            skills = []
        try:
            company_history = json.loads(candidate['company_history']) if candidate['company_history'] else []
        except (json.JSONDecodeError, KeyError):
            company_history = []
        return jsonify({
            'id': candidate['id'],
            'name': candidate['name'],
            'email': candidate['email'],
            'phone': candidate['phone'],
            'company': candidate['company'],
            'designation': candidate['designation'],
            'skills': skills,
            'company_history': company_history,
            'confidence': 0.95,
            'telegram_username': candidate['telegram_username']
        })
    return jsonify({'error': 'Candidate not found'}), 404

@app.route('/candidates/<id>/request-documents', methods=['POST'])
def request_documents(id):
    with get_db() as conn:
        candidate = conn.execute('SELECT name FROM candidates WHERE id = ?', (id,)).fetchone()
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    # AI generated request
    request_text = f"Dear {candidate['name']}, please provide your PAN and Aadhaar documents for verification."
    request_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    with get_db() as conn:
        conn.execute('INSERT INTO requests (id, candidate_id, request_text, timestamp) VALUES (?, ?, ?, ?)',
                     (request_id, id, request_text, timestamp))
    
    return jsonify({'request_id': request_id, 'message': request_text}), 200

@app.route('/candidates/<id>/submit-documents', methods=['POST'])
def submit_documents(id):
    with get_db() as conn:
        candidate = conn.execute('SELECT id FROM candidates WHERE id = ?', (id,)).fetchone()
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    if 'pan' not in request.files or 'aadhaar' not in request.files:
        return jsonify({'error': 'Both PAN and Aadhaar required'}), 400
    
    pan_file = request.files['pan']
    aadhaar_file = request.files['aadhaar']
    
    if pan_file and aadhaar_file:
        pan_filename = secure_filename(pan_file.filename)
        aadhaar_filename = secure_filename(aadhaar_file.filename)
        
        pan_path = os.path.join(app.config['UPLOAD_FOLDER'], pan_filename)
        aadhaar_path = os.path.join(app.config['UPLOAD_FOLDER'], aadhaar_filename)
        
        pan_file.save(pan_path)
        aadhaar_file.save(aadhaar_path)
        
        with get_db() as conn:
            conn.execute('INSERT INTO documents (id, candidate_id, type, path) VALUES (?, ?, ?, ?)',
                         (str(uuid.uuid4()), id, 'PAN', pan_path))
            conn.execute('INSERT INTO documents (id, candidate_id, type, path) VALUES (?, ?, ?, ?)',
                         (str(uuid.uuid4()), id, 'Aadhaar', aadhaar_path))
        
        return jsonify({'message': 'Documents submitted successfully'}), 200
    return jsonify({'message': 'Documents submitted successfully'}), 200
    return jsonify({'error': 'Invalid files'}), 400

@app.route('/candidates/<id>/telegram', methods=['POST'])
def update_telegram(id):
    data = request.get_json()
    telegram_username = data.get('telegram_username')
    if not telegram_username:
        return jsonify({'error': 'telegram_username required'}), 400
    
    with get_db() as conn:
        conn.execute('UPDATE candidates SET telegram_username = ? WHERE id = ?', (telegram_username, id))
    
    return jsonify({'message': 'Telegram username updated'}), 200

@app.route('/candidates/<id>/documents', methods=['GET'])
def get_documents(id):
    with get_db() as conn:
        documents = conn.execute('SELECT type, path, status FROM documents WHERE candidate_id = ?', (id,)).fetchall()
    result = [{'type': d['type'], 'path': d['path'], 'status': d['status']} for d in documents]
    return jsonify(result)


@app.route('/candidates/<id>', methods=['DELETE'])
def delete_candidate(id):
    with get_db() as conn:
        candidate = conn.execute(
            'SELECT id, resume_path FROM candidates WHERE id = ?',
            (id,)
        ).fetchone()
        if not candidate:
            return jsonify({'error': 'Candidate not found'}), 404

        documents = conn.execute(
            'SELECT path FROM documents WHERE candidate_id = ?',
            (id,)
        ).fetchall()

    file_paths = []
    if candidate['resume_path']:
        file_paths.append(candidate['resume_path'])
    file_paths.extend([doc['path'] for doc in documents if doc['path']])

    with get_db() as conn:
        conn.execute('DELETE FROM documents WHERE candidate_id = ?', (id,))
        conn.execute('DELETE FROM requests WHERE candidate_id = ?', (id,))
        conn.execute('DELETE FROM candidates WHERE id = ?', (id,))

    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as exc:
            print(f'Warning: failed to delete file {path}: {exc}')

    return jsonify({'message': 'Candidate profile and files deleted permanently'}), 200

if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port, debug=app.config['DEBUG'])

from flask import Flask, request, jsonify, send_from_directory
import os
import sqlite3
import json
from werkzeug.utils import secure_filename
import re
from datetime import datetime
import uuid
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

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
            resume_path TEXT
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

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_resume_data(file_path, filename):
    # Mock extraction - in real app, use NLP libraries
    name = "John Doe"
    email = "john.doe@example.com"
    phone = "+1234567890"
    company = "Example Corp"
    designation = "Software Engineer"
    skills = ["Python", "Flask", "SQL"]
    return {
        'name': name,
        'email': email,
        'phone': phone,
        'company': company,
        'designation': designation,
        'skills': skills
    }

@app.route('/candidates/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        data = extract_resume_data(file_path, filename)
        candidate_id = str(uuid.uuid4())
        
        with get_db() as conn:
            conn.execute('INSERT INTO candidates (id, name, email, phone, company, designation, skills, resume_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                         (candidate_id, data['name'], data['email'], data['phone'], data['company'], data['designation'], json.dumps(data['skills']), file_path))
        
        return jsonify({'id': candidate_id, 'message': 'Resume uploaded successfully'}), 201
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/candidates', methods=['GET'])
def list_candidates():
    with get_db() as conn:
        candidates = conn.execute('SELECT id, name, email, phone, company, designation, skills FROM candidates').fetchall()
    result = []
    for c in candidates:
        result.append({
            'id': c['id'],
            'name': c['name'],
            'email': c['email'],
            'phone': c['phone'],
            'company': c['company'],
            'designation': c['designation'],
            'skills': json.loads(c['skills'])
        })
    return jsonify(result)

@app.route('/candidates/<id>', methods=['GET'])
def get_candidate(id):
    with get_db() as conn:
        candidate = conn.execute('SELECT * FROM candidates WHERE id = ?', (id,)).fetchone()
    if candidate:
        return jsonify({
            'id': candidate['id'],
            'name': candidate['name'],
            'email': candidate['email'],
            'phone': candidate['phone'],
            'company': candidate['company'],
            'designation': candidate['designation'],
            'skills': json.loads(candidate['skills'])
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
    return jsonify({'error': 'Invalid files'}), 400

if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port, debug=app.config['DEBUG'])
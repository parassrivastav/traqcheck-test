from flask import Flask, request, jsonify, send_file
import os
import sqlite3
import json
from werkzeug.utils import secure_filename
import re
from datetime import datetime
import uuid
from dotenv import load_dotenv
from flask_cors import CORS
from urllib import request as urllib_request
from urllib import parse as urllib_parse
from urllib.error import HTTPError, URLError
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
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
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_API_TOKEN') or os.environ.get('TELEGRAM_API_KEY')
TELEGRAM_WEBHOOK_SECRET = os.environ.get('TELEGRAM_WEBHOOK_SECRET', '')
PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', '').rstrip('/')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SESSION_STAGE_DONE = 'done'
SESSION_STAGE_PAN = 'pan'
SESSION_STAGE_AADHAAR = 'aadhaar'


def candidate_display_name(candidate):
    name = ''
    if candidate:
        if isinstance(candidate, dict):
            name = str(candidate.get('name') or '').strip()
        else:
            try:
                name = str(candidate['name'] or '').strip()
            except (KeyError, TypeError, IndexError):
                name = ''
    return name or 'there'


def mr_traqchecker_intro_message(candidate):
    name = candidate_display_name(candidate)
    return (
        f"Hi {name} I am Mr Traqchecker from Traqcheckjobs.com. "
        "Please provide your Aadhaar and PAN card. "
        "You can send image, PDF, or text details. "
        "I will help you complete this verification."
    )


def mr_traqchecker_ready_message(candidate):
    name = candidate_display_name(candidate)
    return (
        f"Hi {name}, I am Mr Traqchecker from Traqcheckjobs.com. "
        "I am ready to collect your PAN and Aadhaar documents."
    )

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
        conn.execute('''CREATE TABLE IF NOT EXISTS telegram_links (
            candidate_id TEXT PRIMARY KEY,
            chat_id TEXT,
            telegram_identity TEXT,
            updated_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS telegram_sessions (
            chat_id TEXT PRIMARY KEY,
            candidate_id TEXT,
            stage TEXT,
            history TEXT,
            updated_at TEXT
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


def now_iso():
    return datetime.now().isoformat()


def normalize_contact(value):
    if not value:
        return ''
    text = str(value).strip()
    if text.startswith('@'):
        return text[1:].lower()
    digits = re.sub(r'[^0-9]', '', text)
    if len(digits) >= 7:
        return digits
    return text.lower()


def is_numeric_chat_id(value):
    if value is None:
        return False
    return bool(re.fullmatch(r'-?\d{7,}', str(value).strip()))


def telegram_api_call(method, payload=None):
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError('Telegram bot token is not configured')
    payload = payload or {}
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}'
    data = urllib_parse.urlencode(payload).encode('utf-8')
    req = urllib_request.Request(url, data=data, method='POST')
    with urllib_request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode('utf-8'))
    if not body.get('ok'):
        raise RuntimeError(body.get('description', 'Telegram API request failed'))
    return body.get('result')


def telegram_get_file(file_id):
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError('Telegram bot token is not configured')
    file_info = telegram_api_call('getFile', {'file_id': file_id})
    file_path = file_info.get('file_path')
    if not file_path:
        raise RuntimeError('Telegram file path not found')
    url = f'https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}'
    with urllib_request.urlopen(url, timeout=30) as resp:
        content = resp.read()
    return file_path, content


def telegram_send_message(chat_id, text):
    return telegram_api_call('sendMessage', {'chat_id': str(chat_id), 'text': text})


def get_candidate_by_id(candidate_id):
    with get_db() as conn:
        return conn.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()


def find_candidate_for_identity(identity, username=None):
    identity_normalized = normalize_contact(identity)
    username_normalized = normalize_contact(username)
    with get_db() as conn:
        if identity_normalized:
            candidate = conn.execute(
                'SELECT * FROM candidates WHERE lower(replace(replace(replace(phone, "+", ""), "-", ""), " ", "")) = ? '
                'OR lower(replace(telegram_username, "@", "")) = ?',
                (identity_normalized, identity_normalized)
            ).fetchone()
            if candidate:
                return candidate
        if username_normalized:
            candidate = conn.execute(
                'SELECT * FROM candidates WHERE lower(replace(telegram_username, "@", "")) = ?',
                (username_normalized,)
            ).fetchone()
            if candidate:
                return candidate
    return None


def get_candidate_by_chat_id(chat_id):
    with get_db() as conn:
        candidate = conn.execute(
            'SELECT c.* FROM telegram_links tl '
            'JOIN candidates c ON c.id = tl.candidate_id '
            'WHERE tl.chat_id = ? '
            'ORDER BY tl.updated_at DESC '
            'LIMIT 1',
            (str(chat_id),)
        ).fetchone()
        return candidate


def upsert_telegram_link(candidate_id, chat_id, telegram_identity=''):
    with get_db() as conn:
        # Keep chat_id mapped to a single latest candidate to avoid stale lookups.
        conn.execute(
            'DELETE FROM telegram_links WHERE chat_id = ? AND candidate_id != ?',
            (str(chat_id), candidate_id)
        )
        conn.execute(
            'INSERT INTO telegram_links (candidate_id, chat_id, telegram_identity, updated_at) VALUES (?, ?, ?, ?) '
            'ON CONFLICT(candidate_id) DO UPDATE SET chat_id = excluded.chat_id, telegram_identity = excluded.telegram_identity, updated_at = excluded.updated_at',
            (candidate_id, str(chat_id), telegram_identity, now_iso())
        )


def get_telegram_link_for_candidate(candidate_id):
    with get_db() as conn:
        return conn.execute(
            'SELECT chat_id, telegram_identity FROM telegram_links WHERE candidate_id = ?',
            (candidate_id,)
        ).fetchone()


def get_session(chat_id):
    with get_db() as conn:
        return conn.execute(
            'SELECT chat_id, candidate_id, stage, history FROM telegram_sessions WHERE chat_id = ?',
            (str(chat_id),)
        ).fetchone()


def upsert_session(chat_id, candidate_id, stage, history=''):
    with get_db() as conn:
        conn.execute(
            'INSERT INTO telegram_sessions (chat_id, candidate_id, stage, history, updated_at) VALUES (?, ?, ?, ?, ?) '
            'ON CONFLICT(chat_id) DO UPDATE SET candidate_id = excluded.candidate_id, stage = excluded.stage, history = excluded.history, updated_at = excluded.updated_at',
            (str(chat_id), candidate_id, stage, history, now_iso())
        )


def append_session_history(chat_id, speaker, text):
    session = get_session(chat_id)
    history = (session['history'] if session else '') or ''
    updated = (history + f'\n{speaker}: {text}').strip()
    if session:
        upsert_session(chat_id, session['candidate_id'], session['stage'], updated)


def delete_session(chat_id):
    with get_db() as conn:
        conn.execute('DELETE FROM telegram_sessions WHERE chat_id = ?', (str(chat_id),))


def save_document(candidate_id, doc_type, file_path):
    with get_db() as conn:
        conn.execute(
            'INSERT INTO documents (id, candidate_id, type, path, status) VALUES (?, ?, ?, ?, ?)',
            (str(uuid.uuid4()), candidate_id, doc_type, file_path, 'collected')
        )


def mr_traqchecker_response(stage, user_text, history):
    openai_key = os.environ.get('OPENAI_API_KEY')
    if not openai_key:
        if stage == SESSION_STAGE_PAN:
            return 'Please share your PAN document (image, PDF, or text).'
        if stage == SESSION_STAGE_AADHAAR:
            return 'Thanks. Now please share your Aadhaar document (image, PDF, or text).'
        return 'Thanks. I have collected your documents.'

    stage_instruction = {
        SESSION_STAGE_PAN: 'You are currently collecting PAN first.',
        SESSION_STAGE_AADHAAR: 'You are currently collecting Aadhaar now.',
        SESSION_STAGE_DONE: 'Documents are already collected.',
    }.get(stage, 'You are collecting PAN and Aadhaar documents.')

    prompt = PromptTemplate(
        input_variables=['history', 'user_input', 'stage_instruction'],
        template=(
            'You are Mr Traqchecker from Traqcheckjobs.com.\n'
            'Goal: collect PAN and Aadhaar documents over Telegram with polite natural language.\n'
            '{stage_instruction}\n'
            'Stay focused on document collection and do not deviate from this agenda.\n'
            'Keep replies concise (max 3 short sentences).\n'
            'Conversation history:\n{history}\n'
            'User message:\n{user_input}\n'
            'Assistant reply:'
        ),
    )
    llm = ChatOpenAI(temperature=0.2, openai_api_key=openai_key)
    chain = prompt | llm
    result = chain.invoke(
        {
            'history': history or 'No prior history.',
            'user_input': user_text or '',
            'stage_instruction': stage_instruction,
        }
    )
    if hasattr(result, 'content'):
        return str(result.content).strip()
    return result.strip()


def start_document_collection(chat_id, candidate):
    upsert_session(chat_id, candidate['id'], SESSION_STAGE_PAN, '')
    telegram_send_message(chat_id, mr_traqchecker_intro_message(candidate))
    telegram_send_message(chat_id, 'Please share your PAN document first.')

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
        candidate = conn.execute('SELECT id, name, phone, telegram_username FROM candidates WHERE id = ?', (id,)).fetchone()
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404

    request_text = mr_traqchecker_intro_message(candidate)
    request_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    with get_db() as conn:
        conn.execute('INSERT INTO requests (id, candidate_id, request_text, timestamp) VALUES (?, ?, ?, ?)',
                     (request_id, id, request_text, timestamp))

    if not TELEGRAM_BOT_TOKEN:
        return jsonify({
            'error': 'Telegram bot is not configured. Set TELEGRAM_API_TOKEN or TELEGRAM_API_KEY.',
            'request_id': request_id
        }), 500

    link = get_telegram_link_for_candidate(id)
    chat_id = link['chat_id'] if link else None

    if not chat_id:
        candidate_identity = candidate['telegram_username'] or candidate['phone'] or ''
        if is_numeric_chat_id(candidate_identity):
            chat_id = str(candidate_identity).strip()

    if not chat_id:
        return jsonify({
            'request_id': request_id,
            'error': 'Candidate has no linked Telegram chat. Ask candidate to message the bot and send /start <phone_number> once.',
            'link_required': True
        }), 409

    try:
        start_document_collection(chat_id, candidate)
    except Exception as exc:
        return jsonify({
            'request_id': request_id,
            'error': f'Failed to notify candidate on Telegram: {exc}'
        }), 502

    return jsonify({
        'request_id': request_id,
        'message': 'Mr Traqchecker has initiated document collection on Telegram.'
    }), 200

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


def extract_start_identity(text):
    text = (text or '').strip()
    if not text.lower().startswith('/start'):
        return ''
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ''


def save_telegram_text_as_document(candidate_id, doc_type, text, chat_id):
    filename = f'{candidate_id}_{doc_type.lower()}_{chat_id}_{int(datetime.now().timestamp())}.txt'
    path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text or '')
    save_document(candidate_id, doc_type, path)
    return path


def save_telegram_file_as_document(candidate_id, doc_type, file_id, suggested_ext, chat_id):
    tg_path, content = telegram_get_file(file_id)
    ext = suggested_ext or os.path.splitext(tg_path)[1] or '.bin'
    filename = f'{candidate_id}_{doc_type.lower()}_{chat_id}_{int(datetime.now().timestamp())}{ext}'
    path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    with open(path, 'wb') as f:
        f.write(content)
    save_document(candidate_id, doc_type, path)
    return path


def process_telegram_update(update):
    message = update.get('message') or update.get('edited_message')
    if not message:
        return

    chat = message.get('chat') or {}
    chat_id = chat.get('id')
    if chat_id is None:
        return
    chat_id = str(chat_id)

    user = message.get('from') or {}
    username = user.get('username') or ''
    text = message.get('text') or message.get('caption') or ''

    session = get_session(chat_id)
    candidate = get_candidate_by_chat_id(chat_id)

    start_identity = extract_start_identity(text)
    if start_identity:
        linked_candidate = find_candidate_for_identity(start_identity, username=username)
        if not linked_candidate:
            telegram_send_message(
                chat_id,
                'Could not find your profile. Please share the same phone number used in your resume application.'
            )
            return
        upsert_telegram_link(linked_candidate['id'], chat_id, username or start_identity)
        candidate = linked_candidate
        session = get_session(chat_id)
        telegram_send_message(
            chat_id,
            mr_traqchecker_ready_message(candidate)
        )
        if not session:
            upsert_session(chat_id, candidate['id'], SESSION_STAGE_PAN, '')
            telegram_send_message(chat_id, 'Please share your PAN document first.')
        return

    if not candidate:
        maybe_candidate = find_candidate_for_identity('', username=username)
        if maybe_candidate:
            upsert_telegram_link(maybe_candidate['id'], chat_id, username)
            candidate = maybe_candidate

    if not candidate:
        telegram_send_message(
            chat_id,
            'Please link your profile first by sending /start <phone_number_used_in_application>.'
        )
        return

    if not session:
        upsert_session(chat_id, candidate['id'], SESSION_STAGE_PAN, '')
        session = get_session(chat_id)

    stage = session['stage']
    history = session['history'] or ''

    try:
        if message.get('photo'):
            photo = message['photo'][-1]
            doc_type = 'PAN' if stage == SESSION_STAGE_PAN else 'Aadhaar'
            save_telegram_file_as_document(candidate['id'], doc_type, photo['file_id'], '.jpg', chat_id)
            append_session_history(chat_id, 'User', f'Uploaded {doc_type} photo')
            if stage == SESSION_STAGE_PAN:
                upsert_session(chat_id, candidate['id'], SESSION_STAGE_AADHAAR, (get_session(chat_id)['history'] or ''))
                telegram_send_message(chat_id, 'PAN received. Please share your Aadhaar document now.')
            else:
                upsert_session(chat_id, candidate['id'], SESSION_STAGE_DONE, (get_session(chat_id)['history'] or ''))
                telegram_send_message(chat_id, 'Aadhaar received. Verification documents are collected. Thank you.')
            return

        if message.get('document'):
            document = message['document']
            file_name = document.get('file_name') or ''
            ext = os.path.splitext(file_name)[1] or '.bin'
            doc_type = 'PAN' if stage == SESSION_STAGE_PAN else 'Aadhaar'
            save_telegram_file_as_document(candidate['id'], doc_type, document['file_id'], ext, chat_id)
            append_session_history(chat_id, 'User', f'Uploaded {doc_type} file')
            if stage == SESSION_STAGE_PAN:
                upsert_session(chat_id, candidate['id'], SESSION_STAGE_AADHAAR, (get_session(chat_id)['history'] or ''))
                telegram_send_message(chat_id, 'PAN received. Please share your Aadhaar document now.')
            else:
                upsert_session(chat_id, candidate['id'], SESSION_STAGE_DONE, (get_session(chat_id)['history'] or ''))
                telegram_send_message(chat_id, 'Aadhaar received. Verification documents are collected. Thank you.')
            return

        if text:
            append_session_history(chat_id, 'User', text)
            if stage in (SESSION_STAGE_PAN, SESSION_STAGE_AADHAAR) and len(re.sub(r'[^0-9A-Za-z]', '', text)) >= 6:
                doc_type = 'PAN' if stage == SESSION_STAGE_PAN else 'Aadhaar'
                save_telegram_text_as_document(candidate['id'], doc_type, text, chat_id)
                if stage == SESSION_STAGE_PAN:
                    upsert_session(chat_id, candidate['id'], SESSION_STAGE_AADHAAR, (get_session(chat_id)['history'] or ''))
                    telegram_send_message(chat_id, 'Text details received for PAN. Please share Aadhaar details or document now.')
                else:
                    upsert_session(chat_id, candidate['id'], SESSION_STAGE_DONE, (get_session(chat_id)['history'] or ''))
                    telegram_send_message(chat_id, 'Text details received for Aadhaar. Verification documents are collected. Thank you.')
                return

            reply = mr_traqchecker_response(stage, text, history)
            append_session_history(chat_id, 'Mr Traqchecker', reply)
            telegram_send_message(chat_id, reply)
            return

        reply = mr_traqchecker_response(stage, '', history)
        telegram_send_message(chat_id, reply)
    except Exception as exc:
        print(f'Telegram processing error: {exc}')
        telegram_send_message(chat_id, 'Sorry, I hit an issue. Please retry sending your PAN/Aadhaar document.')


@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    if TELEGRAM_WEBHOOK_SECRET:
        secret_header = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if secret_header != TELEGRAM_WEBHOOK_SECRET:
            return jsonify({'error': 'Invalid webhook secret'}), 403
    update = request.get_json(silent=True) or {}
    process_telegram_update(update)
    return jsonify({'ok': True}), 200


@app.route('/telegram/setup-webhook', methods=['POST'])
def setup_telegram_webhook():
    if not TELEGRAM_BOT_TOKEN:
        return jsonify({'error': 'Telegram bot token is not configured'}), 500
    if not PUBLIC_BASE_URL:
        return jsonify({'error': 'PUBLIC_BASE_URL is not configured'}), 500

    webhook_url = f'{PUBLIC_BASE_URL}/telegram/webhook'
    payload = {'url': webhook_url}
    if TELEGRAM_WEBHOOK_SECRET:
        payload['secret_token'] = TELEGRAM_WEBHOOK_SECRET

    try:
        telegram_api_call('setWebhook', payload)
    except (RuntimeError, HTTPError, URLError) as exc:
        return jsonify({'error': f'Failed to set webhook: {exc}'}), 502

    return jsonify({
        'message': 'Telegram webhook configured',
        'webhook_url': webhook_url
    }), 200


@app.route('/telegram/webhook-info', methods=['GET'])
def telegram_webhook_info():
    if not TELEGRAM_BOT_TOKEN:
        return jsonify({'error': 'Telegram bot token is not configured'}), 500
    try:
        info = telegram_api_call('getWebhookInfo')
    except (RuntimeError, HTTPError, URLError) as exc:
        return jsonify({'error': f'Failed to fetch webhook info: {exc}'}), 502
    return jsonify(info), 200

@app.route('/candidates/<id>/documents', methods=['GET'])
def get_documents(id):
    with get_db() as conn:
        documents = conn.execute('SELECT id, type, path, status FROM documents WHERE candidate_id = ? ORDER BY rowid DESC', (id,)).fetchall()
    result = [{
        'id': d['id'],
        'type': d['type'],
        'path': d['path'],
        'status': d['status'],
        'file_url': f"/documents/{d['id']}/file"
    } for d in documents]
    return jsonify(result)


@app.route('/documents/<doc_id>/file', methods=['GET'])
def get_document_file(doc_id):
    with get_db() as conn:
        doc = conn.execute('SELECT path FROM documents WHERE id = ?', (doc_id,)).fetchone()
    if not doc:
        return jsonify({'error': 'Document not found'}), 404

    file_path = doc['path']
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Document file missing'}), 404

    return send_file(file_path, as_attachment=False)


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

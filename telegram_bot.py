import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
import requests
import sqlite3
import json
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DATABASE = os.getenv('DATABASE', 'database.db')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')

# In-memory storage for conversation states
user_states = {}  # chat_id: {'candidate_id': id, 'step': 'pan' or 'aadhaar', 'chain': ConversationChain}

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_candidate_by_telegram(username):
    with get_db() as conn:
        candidate = conn.execute('SELECT * FROM candidates WHERE telegram_username = ?', (username,)).fetchone()
    return candidate

def save_document(candidate_id, doc_type, file_path):
    with get_db() as conn:
        conn.execute('INSERT INTO documents (id, candidate_id, type, path, status) VALUES (?, ?, ?, ?, ?)',
                     (str(uuid.uuid4()), candidate_id, doc_type, file_path, 'collected'))

async def start_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    if not username:
        await update.message.reply_text("Please set a username in Telegram to proceed.")
        return

    candidate = get_candidate_by_telegram(username)
    if not candidate:
        await update.message.reply_text("You are not registered as a candidate. Please contact support.")
        return

    chat_id = update.effective_chat.id
    user_states[chat_id] = {
        'candidate_id': candidate['id'],
        'step': 'pan',
        'chain': create_conversation_chain()
    }

    await update.message.reply_text("Hello! I'm here to help you submit your documents. Please send your PAN card image first.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_states:
        await update.message.reply_text("Please start with /start to begin document submission.")
        return

    state = user_states[chat_id]
    chain = state['chain']

    if update.message.photo:
        # Handle photo upload
        photo = update.message.photo[-1]  # Get the highest resolution
        file = await photo.get_file()
        
        # Download the file
        file_path = os.path.join(UPLOAD_FOLDER, f"{chat_id}_{state['step']}.jpg")
        await file.download_to_drive(file_path)
        
        # Save to database
        save_document(state['candidate_id'], state['step'].upper(), file_path)
        
        if state['step'] == 'pan':
            state['step'] = 'aadhaar'
            await update.message.reply_text("Thank you for the PAN card. Now please send your Aadhaar card image.")
        else:
            # Completed
            await update.message.reply_text("Thank you! All documents have been received. Your submission is complete.")
            del user_states[chat_id]
    else:
        # Use LangChain for conversational response
        response = chain.predict(input=update.message.text)
        await update.message.reply_text(response)

def create_conversation_chain():
    llm = ChatOpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)
    
    template = """You are a helpful assistant helping candidates submit their documents for verification.
    
    Current conversation:
    {history}
    Human: {input}
    Assistant:"""
    
    prompt = PromptTemplate(input_variables=["history", "input"], template=template)
    
    memory = ConversationBufferMemory()
    
    chain = ConversationChain(
        llm=llm,
        prompt=prompt,
        memory=memory,
        verbose=False
    )
    
    return chain

async def main():
    application = Application.builder().token(TELEGRAM_API_KEY).build()

    application.add_handler(CommandHandler("start", start_conversation))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    await application.run_polling()

if __name__ == '__main__':
    import uuid
    asyncio.run(main())
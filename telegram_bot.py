import os
import sqlite3
import uuid

from dotenv import load_dotenv
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE = os.getenv("DATABASE", "database.db")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# chat_id -> {'candidate_id': id, 'step': 'pan'|'aadhaar', 'chain': ConversationChain|None}
user_states = {}


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def get_candidate_by_telegram(username):
    with get_db() as conn:
        candidate = conn.execute(
            "SELECT * FROM candidates WHERE telegram_username = ?",
            (username,),
        ).fetchone()
    return candidate


def save_document(candidate_id, doc_type, file_path):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO documents (id, candidate_id, type, path, status) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), candidate_id, doc_type, file_path, "collected"),
        )


def create_conversation_chain():
    if not OPENAI_API_KEY:
        return None

    llm = ChatOpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)
    template = """You are a helpful assistant helping candidates submit their documents for verification.
Current conversation:
{history}
Human: {input}
Assistant:"""
    prompt = PromptTemplate(input_variables=["history", "input"], template=template)
    memory = ConversationBufferMemory()
    return ConversationChain(llm=llm, prompt=prompt, memory=memory, verbose=False)


async def start_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    if not username:
        await update.message.reply_text("Please set a username in Telegram to proceed.")
        return

    candidate = get_candidate_by_telegram(username)
    if not candidate:
        await update.message.reply_text(
            "You are not registered as a candidate. Please contact support."
        )
        return

    chat_id = update.effective_chat.id
    user_states[chat_id] = {
        "candidate_id": candidate["id"],
        "step": "pan",
        "chain": create_conversation_chain(),
    }
    await update.message.reply_text(
        "Hello! Please send your PAN card image first."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_states:
        await update.message.reply_text("Please start with /start to begin.")
        return

    state = user_states[chat_id]
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        file_path = os.path.join(UPLOAD_FOLDER, f"{chat_id}_{state['step']}.jpg")
        await file.download_to_drive(file_path)
        save_document(state["candidate_id"], state["step"].upper(), file_path)

        if state["step"] == "pan":
            state["step"] = "aadhaar"
            await update.message.reply_text(
                "PAN received. Now send your Aadhaar card image."
            )
        else:
            await update.message.reply_text("All documents received. Thank you.")
            del user_states[chat_id]
        return

    chain = state.get("chain")
    if chain and update.message.text:
        response = chain.predict(input=update.message.text)
        await update.message.reply_text(response)
    else:
        await update.message.reply_text(
            "Please send the requested PAN/Aadhaar image to continue."
        )


def main():
    if not TELEGRAM_API_KEY:
        raise RuntimeError("TELEGRAM_API_KEY is not set.")

    application = Application.builder().token(TELEGRAM_API_KEY).build()
    application.add_handler(CommandHandler("start", start_conversation))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    application.run_polling()


if __name__ == "__main__":
    main()

import os
import tempfile
from pathlib import Path

import telebot
from dotenv import load_dotenv
from main import run_turn, conversations

load_dotenv()

bot = telebot.TeleBot(token=os.getenv("token"))

ALLOWED_USER_ID = os.getenv("user_id")


def allowed(message):
    return int(message.from_user.id) == int(ALLOWED_USER_ID)

def send(chat_id, text):

    if text is None:
        text = "empty reply"

    bot.send_message(chat_id, text)


@bot.message_handler(commands=["start", "kettik"])
def start(message):

    if not allowed(message):
        return

    send(message.chat.id, "Yo, I am your calendar assistant." \
    "I can create, check, update events in your calendar. Tell me which one do you need, kettik!")


@bot.message_handler(commands=["reset"])
def reset(message):

    if not allowed(message):
        return

    if conversations.get(message.chat.id, None) is not None:
        conversations.pop(message.chat.id)

    send(message.chat.id, "Conversation cleared")


@bot.message_handler(content_types=["photo", "document"])
def file(message):

    if not allowed(message):
        return

    if message.content_type == "photo":
        telegram_file_id = message.photo[-1].file_id
        suffix = ".jpg"
    else:
        telegram_file_id = message.document.file_id
        suffix = Path(message.document.file_name or "").suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}:
            send(message.chat.id, "Please upload a JPG, PNG, WEBP, GIF image, or PDF document.")
            return

    bot.send_chat_action(message.chat.id, "typing")
    telegram_file = bot.get_file(telegram_file_id)
    file_bytes = bot.download_file(telegram_file.file_path)

    with tempfile.TemporaryDirectory() as directory:
        file_path = Path(directory) / f"telegram_upload{suffix}"
        file_path.write_bytes(file_bytes)

        prompt = (
            f"{message.caption}\n\n" if message.caption else
            "Please read the uploaded file and extract its calendar events.\n\n"
        )
        prompt += f"Uploaded file path: {file_path}"
        send(message.chat.id, run_turn(message.chat.id, prompt))


@bot.message_handler(content_types=["text"])
def text(message):

    if not allowed(message):
        return

    bot.send_chat_action(message.chat.id, "typing")
    send(message.chat.id, run_turn(message.chat.id, message.text))



if __name__ == "__main__":

    print("Bot is running...")
    bot.remove_webhook()

    bot.infinity_polling(skip_pending=True)

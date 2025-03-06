import os
import json
import random
import logging
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ChatAction

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Constants
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CACHE_DURATION = timedelta(minutes=30)
RATE_LIMIT_DURATION = timedelta(minutes=1)
MAX_REQUESTS_PER_MINUTE = 2
TIME_BUTTON_TEXT = "⏰ What Time Is It?"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/tengfone/clockblocker",
}

# Cache structure
cache = {
    "philosophical_discussion": {"text": None, "timestamp": None},
    "absurd_guess": {"text": None, "timestamp": None},
}

# Rate limiting structure: user_id -> list of request timestamps
rate_limit_store = defaultdict(list)


def cleanup_rate_limit_store():
    """Remove entries older than 1 minute from the rate limit store"""
    current_time = datetime.now()
    for user_id in list(rate_limit_store.keys()):
        # Keep only timestamps that are within the last minute
        rate_limit_store[user_id] = [
            timestamp
            for timestamp in rate_limit_store[user_id]
            if current_time - timestamp < RATE_LIMIT_DURATION
        ]
        # Remove user entry if they have no recent requests
        if not rate_limit_store[user_id]:
            del rate_limit_store[user_id]


def is_rate_limited(user_id: int) -> bool:
    """Check if a user has exceeded their rate limit"""
    cleanup_rate_limit_store()
    recent_requests = len(rate_limit_store[user_id])
    return recent_requests >= MAX_REQUESTS_PER_MINUTE


def update_rate_limit(user_id: int):
    """Add a new request timestamp for the user"""
    rate_limit_store[user_id].append(datetime.now())


def get_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(TIME_BUTTON_TEXT)]], resize_keyboard=True, is_persistent=True
    )


def is_cache_valid(cache_type):
    if not cache[cache_type]["timestamp"]:
        return False
    return datetime.now() - cache[cache_type]["timestamp"] < CACHE_DURATION


async def get_ai_response(prompt, model="deepseek/deepseek-chat:free"):
    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=HEADERS,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"Error with {model}: {str(e)}")
        if model == "deepseek/deepseek-chat:free":
            return await get_ai_response(prompt, "deepseek/deepseek-chat")
        return "My temporal consciousness seems to be malfunctioning... 🤖"


async def philosophical_time_discussion():
    if is_cache_valid("philosophical_discussion"):
        return cache["philosophical_discussion"]["text"]

    prompt = """
    Provide a brief but profound philosophical discussion about the nature of time.
    Make it somewhat humorous but also genuinely thought-provoking.
    Keep it under 150 words.
    """
    response = await get_ai_response(prompt)
    cache["philosophical_discussion"] = {"text": response, "timestamp": datetime.now()}
    return response


async def absurd_time_guess():
    if is_cache_valid("absurd_guess"):
        return cache["absurd_guess"]["text"]

    prompt = """
    Make an absurd guess about what time it is right now using extremely questionable logic.
    Be creative and humorous. Keep it under 100 words.
    """
    response = await get_ai_response(prompt)
    cache["absurd_guess"] = {"text": response, "timestamp": datetime.now()}
    return response


async def ridiculous_time_estimation():
    methods = [
        "Based on my analysis of current internet meme trends, which clearly indicate a temporal shift in the collective consciousness...",
        "By measuring the quantum fluctuations in my CPU's processing speed and converting them to temporal coordinates...",
        "After consulting the ancient art of chronological divination through random number generation...",
        "Using advanced calculations based on the number of cat videos posted in the last hour...",
        "By interpreting the cosmic background radiation as a temporal signal...",
    ]
    return f"{random.choice(methods)} I estimate it's {random.randint(1, 12)}:{random.randint(0, 59)} {'AM' if random.random() > 0.5 else 'PM'}!"


async def time_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the chat_id and message_id for editing
    if update.callback_query:
        chat_id = update.callback_query.message.chat_id
        message_id = update.callback_query.message.message_id
        # Answer the callback query to remove the loading state
        await update.callback_query.answer()
    else:
        chat_id = update.effective_chat.id
        message_id = None

    # Step 1: Philosophical discussion
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    intro_message = await context.bot.send_message(
        chat_id=chat_id,
        text="🤔 Before I tell you the time, let's ponder the nature of time itself...",
    )

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    philosophy = await philosophical_time_discussion()
    await context.bot.send_message(chat_id=chat_id, text=philosophy)

    # Step 2: AI's absurd guess
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await context.bot.send_message(
        chat_id=chat_id,
        text="🔮 Now, let me make an educated guess about the current time...",
    )

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    guess = await absurd_time_guess()
    await context.bot.send_message(chat_id=chat_id, text=guess)

    # Step 3: Ridiculous estimation method
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await context.bot.send_message(
        chat_id=chat_id,
        text="🧪 That didn't feel right. Let me try a more scientific approach...",
    )

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    estimation = await ridiculous_time_estimation()
    await context.bot.send_message(chat_id=chat_id, text=estimation)

    # Step 4: Give up and provide link
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "😅 *sigh* You know what? I give up.\n\n"
            "After all this philosophical contemplation, wild guessing, and questionable scientific methods, "
            "maybe you should just check the time yourself:\n\n"
            "🔗 https://www.clockfaceonline.co.uk/clocks/digital/\n\n"
            "(I'll be here questioning the nature of temporal reality if you need me again...)"
        ),
        parse_mode="Markdown",
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "🌟 Welcome to the most overengineered time-telling bot ever created!\n\n"
        "I don't simply tell you the time - I take you on a journey through the very fabric of temporal existence. "
        "Prepare yourself for philosophical musings, wild guesses, and questionable scientific methods.\n\n"
        "Use the button below to begin your temporal adventure!"
    )

    await update.message.reply_text(welcome_message, reply_markup=get_keyboard())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == TIME_BUTTON_TEXT:
        user_id = update.effective_user.id

        if is_rate_limited(user_id):
            remaining_time = RATE_LIMIT_DURATION - (
                datetime.now() - rate_limit_store[user_id][0]
            )
            seconds_remaining = int(remaining_time.total_seconds())
            await update.message.reply_text(
                f"⏳ Whoa there, time enthusiast! You're moving too fast through the temporal plane.\n\n"
                f"Please wait {seconds_remaining} seconds before embarking on another temporal adventure.\n\n"
                f"Perhaps this is a good moment to contemplate the nature of patience... 🤔"
            )
            return

        update_rate_limit(user_id)
        await time_process(update, context)


def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    application.run_polling()


if __name__ == "__main__":
    main()

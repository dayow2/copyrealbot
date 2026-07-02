import os
import re
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from http import HTTPStatus
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load core environment tokens
BOT_TOKEN = os.getenv("BOT_TOKEN")
RAILWAY_PUBLIC_URL = os.getenv("RAILWAY_PUBLIC_URL") # Provided automatically by Railway

# Initialize Telegram Application
ptb = Application.builder().token(BOT_TOKEN).updater(None).build()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages bot startup and webhook registration when Railway boots the container."""
    if not BOT_TOKEN or not RAILWAY_PUBLIC_URL:
        logger.error("Missing critical environment variables: BOT_TOKEN or RAILWAY_PUBLIC_URL")
    
    webhook_url = f"{RAILWAY_PUBLIC_URL.rstrip('/')}/webhook"
    logger.info(f"Setting webhook target to: {webhook_url}")
    await ptb.bot.set_webhook(url=webhook_url)
    
    async with ptb:
        await ptb.start()
        yield
        await ptb.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def process_telegram_update(request: Request):
    """Listens for direct update payloads pushed from Telegram's servers."""
    try:
        req_json = await request.json()
        update = Update.de_json(req_json, ptb.bot)
        await ptb.process_update(update)
    except Exception as e:
        logger.error(f"Error handling update payload: {e}")
    return Response(status_code=HTTPStatus.OK)

@app.get("/")
async def health_check():
    """Simple connection test endpoint for your web browser."""
    return {"status": "CopyBot is running perfectly!"}

# --- BOT INTERACTION INTERFACE ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers on /start command."""
    welcome_text = (
        "👋 **Welcome to CopyBot!**\n\n"
        "Send me any rough, messy text or copy-paste an article. I will instantly clean up spacing, "
        "strip out hidden link trackers, format it for markdown, and give you key marketing metrics."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def text_processor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Intercepts sent text and generates processing utility options."""
    raw_user_text = update.message.text
    # Temporarily store text in user context dictionary to clean it in the next phase
    context.user_data["current_text"] = raw_user_text

    keyboard = [
        [InlineKeyboardButton("🧹 Pure Clean (Fix Space & Formatting)", callback_data="clean")],
        [InlineKeyboardButton("🔗 Strip URL Tracking Tags", callback_data="strip_links")],
        [InlineKeyboardButton("📊 Count Ad Characters & Words", callback_data="metrics")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a professional tool option below:", reply_markup=reply_markup)

async def button_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes option selection buttons seamlessly."""
    query = update.callback_query
    await query.answer()
    
    user_text = context.user_data.get("current_text", "")
    if not user_text:
        await query.edit_message_text("❌ No text sequence found. Please send your text over again.")
        return

    if query.data == "clean":
        # 1. Clean multiple blank lines down to single breaks, fix trailing whitespaces
        cleaned = re.sub(r'\n\s*\n', '\n\n', user_text).strip()
        cleaned = re.sub(r'[ \t]+', ' ', cleaned) # clean double spacing inside sentences
        output = f"✨ **Your Cleaned Copy:**\n\n```\n{cleaned}\n```"
        await query.edit_message_text(output, parse_mode="Markdown")

    elif query.data == "strip_links":
        # 2. Extract and remove standard UTM/Marketing tracking structures from any link contained inside
        # Removes tracking variables like ?utm_source=, ?fbclid=, etc.
        stripped = re.sub(r'(\?|\&)(utm_[a-z]+|fbclid|gclid|affiliate|ref)=[^&\s]+', '', user_text)
        output = f"🔗 **Cleaned Links (Trackers Removed):**\n\n{stripped}"
        await query.edit_message_text(output)

    elif query.data == "metrics":
        # 3. Calculate metrics for ad copy rules
        char_count = len(user_text)
        word_count = len(user_text.split())
        paragraph_count = len([p for p in user_text.split('\n') if p.strip()])
        
        metrics_dashboard = (
            "📊 **Copy Audit Dashboard**\n"
            "---"
            f"• **Total Characters:** {char_count}\n"
            f"• **Total Words:** {word_count}\n"
            f"• **Paragraph Blocks:** {paragraph_count}\n"
            "---"
            "💡 *Tip: High-converting social captions typically track best under 150 words!*"
        )
        await query.edit_message_text(metrics_dashboard, parse_mode="Markdown")

# Register handlers natively into our pipeline
ptb.add_handler(CommandHandler("start", start_command))
ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_processor))
ptb.add_handler(CallbackQueryHandler(button_dispatcher))

import os
import re
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from http import HTTPStatus
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Super deep logging to force text straight into the Railway Console tab
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Dynamic webhook URL routing based on your Railway project layout
RAILWAY_PUBLIC_URL = os.getenv("RAILWAY_PUBLIC_URL")

if not BOT_TOKEN:
    logger.error("CRITICAL CONFIG ERROR: BOT_TOKEN variable is completely missing inside Railway!")
    sys.exit(1)

# Initialize Telegram Application interface smoothly
ptb = Application.builder().token(BOT_TOKEN).updater(None).build()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages secure application boot and registers webhooks automatically."""
    await ptb.initialize()
    
    if RAILWAY_PUBLIC_URL:
        clean_url = RAILWAY_PUBLIC_URL if RAILWAY_PUBLIC_URL.startswith("http") else f"https://{RAILWAY_PUBLIC_URL}"
        webhook_target = f"{clean_url.rstrip('/')}/webhook"
        logger.info(f"Registering safe webhook link with Telegram: {webhook_target}")
        await ptb.bot.set_webhook(url=webhook_target, drop_pending_updates=True)
    else:
        logger.warning("CRITICAL: RAILWAY_PUBLIC_URL is missing. Please generate a domain in settings!")
        
    await ptb.start()
    yield
    await ptb.stop()
    await ptb.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def handle_telegram_updates(request: Request):
    """Listens for safe operational data streams pushed straight from Telegram."""
    try:
        payload = await request.json()
        update = Update.de_json(payload, ptb.bot)
        await ptb.process_update(update)
    except Exception as e:
        logger.error(f"Error executing payload stream update: {e}")
    return Response(status_code=HTTPStatus.OK)

@app.get("/")
async def homepage_health_check():
    """Simple web verification check to prove the server is awake."""
    return {"status": "CopyBot server engine is live and working perfectly!"}

# --- BOT INTERACTION CODE ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Welcome to CopyBot!**\n\n"
        "Send me any rough text or copy-paste an article. I will instantly clean up spacing, "
        "strip out tracking links, and give you key marketing metrics."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def text_processor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_user_text = update.message.text
    context.user_data["current_text"] = raw_user_text

    keyboard = [
        [InlineKeyboardButton("🧹 Pure Clean (Fix Space & Formatting)", callback_data="clean")],
        [InlineKeyboardButton("🔗 Strip URL Tracking Tags", callback_data="strip_links")],
        [InlineKeyboardButton("📊 Count Ad Characters & Words", callback_data="metrics")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a professional tool option below:", reply_markup=reply_markup)

async def button_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_text = context.user_data.get("current_text", "")
    if not user_text:
        await query.edit_message_text("❌ No text sequence found. Please send your text over again.")
        return

    if query.data == "clean":
        cleaned = re.sub(r'\n\s*\n', '\n\n', user_text).strip()
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        output = f"✨ **Your Cleaned Copy:**\n\n```\n{cleaned}\n```"
        await query.edit_message_text(output, parse_mode="Markdown")

    elif query.data == "strip_links":
        stripped = re.sub(r'(\?|\&)(utm_[a-z]+|fbclid|gclid|affiliate|ref)=[^&\s]+', '', user_text)
        output = f"🔗 **Cleaned Links (Trackers Removed):**\n\n{stripped}"
        await query.edit_message_text(output)

    elif query.data == "metrics":
        char_count = len(user_text)
        word_count = len(user_text.split())
        paragraph_count = len([p for p in user_text.split('\n') if p.strip()])
        
        metrics_dashboard = (
            "📊 **Copy Audit Dashboard**\n"
            "---\n"
            f"• **Total Characters:** {char_count}\n"
            f"• **Total Words:** {word_count}\n"
            f"• **Paragraph Blocks:** {paragraph_count}\n"
            "---\n"
            "💡 *Tip: High-converting social captions typically track best under 150 words!*"
        )
        await query.edit_message_text(metrics_dashboard, parse_mode="Markdown")

# Add handlers
ptb.add_handler(CommandHandler("start", start_command))
ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_processor))
ptb.add_handler(CallbackQueryHandler(button_dispatcher))

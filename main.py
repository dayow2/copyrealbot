import os
import re
import logging
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from http import HTTPStatus
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Deep console logging routing
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
RAILWAY_PUBLIC_URL = os.getenv("RAILWAY_PUBLIC_URL")

if not BOT_TOKEN:
    logger.error("CRITICAL CONFIG ERROR: BOT_TOKEN variable is missing!")
    sys.exit(1)

# Initialize application structure
ptb = Application.builder().token(BOT_TOKEN).build()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages bot execution lifecycle safely across Webhook or Polling methods."""
    await ptb.initialize()
    
    if RAILWAY_PUBLIC_URL:
        # Configuration setup for Webhook routing
        clean_url = RAILWAY_PUBLIC_URL if RAILWAY_PUBLIC_URL.startswith("http") else f"https://{RAILWAY_PUBLIC_URL}"
        webhook_target = f"{clean_url.rstrip('/')}/webhook"
        logger.info(f"Registering Webhook route link: {webhook_target}")
        await ptb.bot.set_webhook(url=webhook_target, drop_pending_updates=True)
        await ptb.start()
    else:
        # Safe structural fallback mechanism if domain isn't generated yet
        logger.warning("No public domain detected. Activating Fallback Polling loop mode...")
        await ptb.bot.delete_webhook(drop_pending_updates=True)
        await ptb.start()
        # Run polling loop inside the background execution pool safely
        asyncio.create_task(ptb.updater.start_polling(drop_pending_updates=True))
        logger.info("Fallback Polling engine loop is online and listening!")
        
    yield
    
    # Secure cleanup handling when container closes down
    if ptb.updater and ptb.updater.is_active:
        await ptb.updater.stop()
    await ptb.stop()
    await ptb.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def handle_telegram_updates(request: Request):
    """Webhook data entry port."""
    try:
        payload = await request.json()
        update = Update.de_json(payload, ptb.bot)
        await ptb.process_update(update)
    except Exception as e:
        logger.error(f"Webhook update processing exception error: {e}")
    return Response(status_code=HTTPStatus.OK)

@app.get("/")
async def homepage_health_check():
    return {"status": "CopyBot application background core is fully functional!"}

# --- INTERACTION CODE INTERFACE ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Executing system /start routine query for user chat thread.")
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

import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Logging to help us see everything inside the Railway Console
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("CRITICAL ERROR: BOT_TOKEN variable is completely missing in Railway!")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Welcome to CopyBot!**\n\n"
        "Send me any rough, messy text. I will instantly clean up spacing, "
        "strip out hidden link trackers, and give you key marketing metrics."
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

def main():
    logger.info("Starting CopyBot in Polling Mode...")
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_processor))
    application.add_handler(CallbackQueryHandler(button_dispatcher))

    logger.info("CopyBot is completely live and listening for messages!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()ispatcher))

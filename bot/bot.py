import io
import logging
import asyncio
import base64
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
import openai_utils
import config
import database

db = database.Database()
logger = logging.getLogger(__name__)
user_semaphores = {}
user_tasks = {}

HELP_MESSAGE = """Commands:
⚪ /retry – Regenerate last bot answer
⚪ /new – Start new dialog
⚪ /mode – Select chat mode
⚪ /settings – Show settings
⚪ /balance – Show balance
⚪ /help – Show help

🎨 Generate images from text prompts in <b>👩‍🎨 Artist</b> /mode
👥 Add bot to <b>group chat</b>: /help_group_chat
🎤 You can send <b>Voice Messages</b> instead of text
"""

HELP_GROUP_CHAT_MESSAGE = """You can add bot to any <b>group chat</b> to help and entertain its participants!

Instructions:
1. Add the bot to the group chat
2. Make it an <b>admin</b>, so that it can see messages (all other rights can be restricted)
3. You're awesome!

To get a reply from the bot in the chat – @ <b>tag</b> it or <b>reply</b> to its message.
For example: "{bot_username} write a poem about Telegram"
"""

def get_chat_mode_menu():
    keyboard = []
    for key, mode in config.chat_modes.items():
        keyboard.append([InlineKeyboardButton(mode['name'], callback_data=f"set_chat_mode|{key}")])
    return "Choose chat mode:", InlineKeyboardMarkup(keyboard)

async def register_user_if_not_exists(update: Update, context: CallbackContext):
    user = update.effective_user
    if not db.check_if_user_exists(user.id):
        db.add_new_user(user.id, update.effective_chat.id, username=user.username, first_name=user.first_name)
        db.start_new_dialog(user.id)
    if user.id not in user_semaphores:
        user_semaphores[user.id] = asyncio.Semaphore(1)

async def start_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context)
    db.start_new_dialog(update.effective_user.id)
    await update.message.reply_text("Hi! I'm your ChatGPT bot 🤖\n\n" + HELP_MESSAGE, parse_mode=ParseMode.HTML)
    text, keyboard = get_chat_mode_menu()
    await update.message.reply_text(text, reply_markup=keyboard)

async def help_handle(update: Update, context: CallbackContext):
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)

async def help_group_chat_handle(update: Update, context: CallbackContext):
    await update.message.reply_text(
        HELP_GROUP_CHAT_MESSAGE.format(bot_username="@" + context.bot.username),
        parse_mode=ParseMode.HTML
    )

async def new_dialog_handle(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    db.start_new_dialog(user_id)
    await update.message.reply_text("Starting new dialog ✅")

async def cancel_handle(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in user_tasks:
        user_tasks[user_id].cancel()
        await update.message.reply_text("✅ Canceled")
    else:
        await update.message.reply_text("<i>Nothing to cancel...</i>", parse_mode=ParseMode.HTML)

async def retry_handle(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    dialog = db.get_dialog_messages(user_id)
    if dialog:
        last = dialog[-1]
        db.set_dialog_messages(user_id, dialog[:-1])
        await message_handle(update, context, message=last['user']['text'])
    else:
        await update.message.reply_text("No previous message to retry.")

async def message_handle(update: Update, context: CallbackContext, message=None):
    await register_user_if_not_exists(update, context)
    user_id = update.effective_user.id
    user_msg = message or update.message.text
    model = db.get_user_attribute(user_id, "current_model") or config.models["available_text_models"][0]
    chat_mode = db.get_user_attribute(user_id, "current_chat_mode") or "assistant"

    async with user_semaphores[user_id]:
        placeholder = await update.message.reply_text("...")
        try:
            dialog = db.get_dialog_messages(user_id)
            chatgpt = openai_utils.ChatGPT(model=model)
            reply, tokens, _ = await chatgpt.send_message(user_msg, dialog_messages=dialog, chat_mode=chat_mode)
            await context.bot.edit_message_text(
                reply[:4096], chat_id=placeholder.chat_id, message_id=placeholder.message_id, parse_mode=ParseMode.HTML
            )
            db.update_n_used_tokens(user_id, model, *tokens)
            db.set_dialog_messages(user_id, dialog + [{"user": {"text": user_msg}, "bot": reply, "date": datetime.now()}])
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await update.message.reply_text("An error occurred. Please try again.")

async def unsupport_message_handle(update: Update, context: CallbackContext):
    await update.message.reply_text("Unsupported file type. Please send text, image, or voice messages only.")

async def voice_message_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context)
    user_id = update.effective_user.id
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    buf.name = "voice.ogg"
    buf.seek(0)
    text = await openai_utils.transcribe_audio(buf)
    await update.message.reply_text(f"🎤: <i>{text}</i>", parse_mode=ParseMode.HTML)
    await message_handle(update, context, message=text)

async def show_chat_modes_handle(update: Update, context: CallbackContext):
    text, keyboard = get_chat_mode_menu()
    await update.message.reply_text(text, reply_markup=keyboard)

async def show_chat_modes_callback_handle(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    text, keyboard = get_chat_mode_menu()
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def set_chat_mode_handle(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    mode = query.data.split("|")[1]
    user_id = query.from_user.id
    db.set_user_attribute(user_id, "current_chat_mode", mode)
    db.start_new_dialog(user_id)
    await query.edit_message_text(f"Switched to {config.chat_modes[mode]['name']} mode ✅", parse_mode=ParseMode.HTML)

async def settings_handle(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    current = db.get_user_attribute(user_id, "current_model")
    buttons = []
    for model in config.models["available_text_models"]:
        label = config.models["info"][model]["name"]
        if model == current:
            label = "✅ " + label
        buttons.append(InlineKeyboardButton(label, callback_data=f"set_settings|{model}"))
    await update.message.reply_text("Choose model:", reply_markup=InlineKeyboardMarkup([buttons]))

async def set_settings_handle(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    model = query.data.split("|")[1]
    user_id = query.from_user.id
    db.set_user_attribute(user_id, "current_model", model)
    db.start_new_dialog(user_id)
    await query.edit_message_text(f"Model set to {config.models['info'][model]['name']} ✅", parse_mode=ParseMode.HTML)

async def show_balance_handle(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    usage = db.get_user_attribute(user_id, "n_used_tokens")
    images = db.get_user_attribute(user_id, "n_generated_images")
    seconds = db.get_user_attribute(user_id, "n_transcribed_seconds")
    total = 0
    details = ""
    for model, usage_data in usage.items():
        inp, out = usage_data["n_input_tokens"], usage_data["n_output_tokens"]
        cost = (inp / 1000) * config.models["info"][model]["price_per_1000_input_tokens"] + \
               (out / 1000) * config.models["info"][model]["price_per_1000_output_tokens"]
        total += cost
        details += f"- {model}: {cost:.3f}$ for {inp + out} tokens\n"
    img_cost = images * config.models["info"]["dalle-2"]["price_per_1_image"]
    voice_cost = (seconds / 60) * config.models["info"]["whisper"]["price_per_1_min"]
    total += img_cost + voice_cost
    details += f"- DALL·E: {img_cost:.3f}$ for {images} images\n"
    details += f"- Whisper: {voice_cost:.3f}$ for {seconds:.1f} seconds\n"
    await update.message.reply_text(f"You spent <b>{total:.3f}$</b>\n\n{details}", parse_mode=ParseMode.HTML)

async def error_handle(update, context):
    logger.error(f"Exception: {context.error}")
    await update.message.reply_text("⚠️ Something went wrong.")

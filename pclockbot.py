# -*- coding: utf-8 -*-
import os
import io
import webbrowser
import pyautogui
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import cv2
import numpy as np
import threading
import time
from telegram.ext import MessageHandler, filters
import psutil
import socket
import platform
from plyer import notification
import random
import pyttsx3
import pyperclip
import requests
import threading
import asyncio
import json
from groq import Groq
import pickle
from huggingface_hub import InferenceClient

GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # получить на console.groq.com
groq_client = Groq(api_key=GROQ_API_KEY)

groq_history = []

HF_API_KEY = os.getenv("HF_API_KEY")
hf_client = InferenceClient(token=HF_API_KEY)

TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = 1266779267
CONTACTS = {
    "алина":  5215525886,    # замени на реальный ID
    "ваня": 1770540509,     # замени на реальный ID
    "мама": 6488268907,
    "я": 7628789542  # замени на реальный ID
}
BLOCKED_USERS_FILE = "blocked_users.json"

# Загрузка при старте
def load_blocked():
    try:
        with open(BLOCKED_USERS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

# Сохранение
def save_blocked():
    with open(BLOCKED_USERS_FILE, "w") as f:
        json.dump(list(BLOCKED_USERS), f)

BLOCKED_USERS = load_blocked()

def check_access(update):
    return update.effective_user.id == ALLOWED_USER_ID

GROQ_HISTORY_FILE = "groq_history.pkl"

def save_groq_history():
    try:
        with open(GROQ_HISTORY_FILE, "wb") as f:
            pickle.dump(groq_history, f)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

def load_groq_history():
    try:
        with open(GROQ_HISTORY_FILE, "rb") as f:
            return pickle.load(f)
    except:
        return []

groq_history = load_groq_history()


async def on_startup(app):
    await app.bot.send_message(chat_id=ALLOWED_USER_ID, text="✅ Бот запущен и готов к работе")


async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    await update.message.reply_text("Выключаю...")
    os.system("shutdown /s /t 5")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    await update.message.reply_text("Перезагружаю...")
    os.system("shutdown /r /t 5")

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    img = pyautogui.screenshot()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    await update.message.reply_photo(photo=buf, caption="Скриншот")

# Словарь ссылок
LINKS = {
    "рикрол": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "ютуб": "https://youtube.com",
    "гугл": "https://google.com",
    # добавляй свои
}

async def openurl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        links_list = "\n".join([f"  • {name}" for name in LINKS.keys()])
        await update.message.reply_text(
            f"Использование: /open рикрол\nили /open https://example.com\n\n"
            f"Доступные ссылки:\n{links_list}"
        )
        return

    query = context.args[0].lower()

    # Проверяем словарь, иначе открываем как прямую ссылку
    url = LINKS.get(query, query)

    if not url.startswith("http"):
        await update.message.reply_text("❌ Ссылка не найдена и не является URL")
        return

    webbrowser.open(url)
    await update.message.reply_text(f"✅ Открыл: {url}")


async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    seconds = 15
    if context.args:
        try:
            seconds = min(int(context.args[0]), 60)  # максимум 60 сек
        except:
            pass

    await update.message.reply_text(f"Записываю экран {seconds} секунд...")

    filename = "record.avi"
    screen = pyautogui.screenshot()
    w, h = screen.size
    out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*"XVID"), 10, (w, h))

    start = time.time()
    while time.time() - start < seconds:
        frame = pyautogui.screenshot()
        frame = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
        out.write(frame)

    out.release()

    with open(filename, "rb") as f:
        await update.message.reply_video(video=f, caption=f"Запись {seconds} сек")

# Словарь контактов — добавляй сюда нужных людей


async def send_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if len(context.args) < 2:
        contacts_list = "\n".join([f"  • {name}" for name in CONTACTS.keys()])
        await update.message.reply_text(
            f"Использование:\n/send алина Привет!\n/send 123456789 Привет!\n\n"
            f"Доступные контакты:\n{contacts_list}"
        )
        return

    target = context.args[0].lower()
    text = " ".join(context.args[1:])

    # Проверяем есть ли в словаре контактов
    chat_id = CONTACTS.get(target, target)  # если не найдено — используем как ID

    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
        await update.message.reply_text("✅ Отправлено")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


# Пересылка всего контента от других пользователей
async def forward_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ALLOWED_USER_ID:
        return
    if update.effective_user.id in BLOCKED_USERS:
        await update.message.reply_text("Вы не можете отправлять сообщения.")
        return
    if update.effective_user.id == ALLOWED_USER_ID:
        return

    user = update.effective_user
    username = f"@{user.username}" if user.username else f"id:{user.id}"
    name = user.full_name or "Без имени"
    msg = update.message

    header = f"📩 От {name} ({username}):"

    try:
        if msg.text:
            await context.bot.send_message(chat_id=ALLOWED_USER_ID, text=f"{header}\n\n{msg.text}")
        elif msg.photo:
            await context.bot.send_photo(chat_id=ALLOWED_USER_ID, photo=msg.photo[-1].file_id, caption=header)
        elif msg.video:
            await context.bot.send_video(chat_id=ALLOWED_USER_ID, video=msg.video.file_id, caption=header)
        elif msg.video_note:
            await context.bot.send_message(chat_id=ALLOWED_USER_ID, text=header)
            await context.bot.send_video_note(chat_id=ALLOWED_USER_ID, video_note=msg.video_note.file_id)
        elif msg.voice:
            await context.bot.send_voice(chat_id=ALLOWED_USER_ID, voice=msg.voice.file_id, caption=header)
        elif msg.audio:
            await context.bot.send_audio(chat_id=ALLOWED_USER_ID, audio=msg.audio.file_id, caption=header)
        elif msg.document:
            await context.bot.send_document(chat_id=ALLOWED_USER_ID, document=msg.document.file_id, caption=header)
        elif msg.sticker:
            await context.bot.send_message(chat_id=ALLOWED_USER_ID, text=f"{header}\n[стикер]")
            await context.bot.send_sticker(chat_id=ALLOWED_USER_ID, sticker=msg.sticker.file_id)
        else:
            await context.bot.send_message(chat_id=ALLOWED_USER_ID, text=f"{header}\n[неизвестный тип сообщения]")
    except Exception as e:
        await context.bot.send_message(chat_id=ALLOWED_USER_ID, text=f"⚠️ Ошибка пересылки: {e}")




async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /notify Текст уведомления")
        return
    text = " ".join(context.args)
    notification.notify(title="Уведомление", message=text, timeout=5)
    await update.message.reply_text("✅ Уведомление отправлено на ПК")




# Информация о системе
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    battery = psutil.sensors_battery()

    battery_info = f"{battery.percent:.0f}% {'🔌' if battery.power_plugged else '🔋'}" if battery else "Нет батареи"

    text = (
        f"💻 *Статус системы:*\n\n"
        f"🖥 CPU: {cpu}%\n"
        f"🧠 RAM: {ram.percent}% ({ram.used // 1024**2} / {ram.total // 1024**2} MB)\n"
        f"💾 Диск: {disk.percent}% ({disk.free // 1024**3} GB свободно)\n"
        f"🔋 Батарея: {battery_info}\n"
        f"⏱ Система: {platform.system()} {platform.release()}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")




# Внешний IP
async def get_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    try:
        import urllib.request
        ip = urllib.request.urlopen("https://api.ipify.org").read().decode()
        await update.message.reply_text(f"🌐 Внешний IP: `{ip}`", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Не удалось получить IP")




# Спящий режим
async def sleep_pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    await update.message.reply_text("😴 Перевожу в спящий режим...")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")




# Громкость
async def volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /volume 50 (0-100)")
        return
    try:
        level = max(0, min(100, int(context.args[0])))
        os.system(f"powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]173)")
        os.system(f"""powershell -c $vol = New-Object -ComObject WScript.Shell; 
                   [audio]::Volume = {level / 100}""")
        await update.message.reply_text(f"🔊 Громкость: {level}%")
    except:
        await update.message.reply_text("❌ Ошибка установки громкости")




async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    result = random.choice(["🪙 Орёл!", "🪙 Решка!"])
    await update.message.reply_text(result)

# /8ball — магический шар
async def eightball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    answers = [
        "✅ Однозначно да", "✅ Скорее всего", "✅ Все признаки говорят да",
        "🤔 Не уверен", "🤔 Спроси позже", "🤔 Лучше не говорить",
        "❌ Даже не думай", "❌ Мой ответ — нет", "❌ Очень сомнительно"
    ]
    if not context.args:
        await update.message.reply_text("Использование: /8ball твой вопрос")
        return
    await update.message.reply_text(f"🎱 {random.choice(answers)}")

# /alarm — огромное уведомление
async def alarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /alarm Текст")
        return
    text = " ".join(context.args)
    notification.notify(title="‼️ ВАЖНО ‼️", message=text, timeout=10)
    await update.message.reply_text("✅ Уведомление отправлено")

# /type — печатает текст на ПК
async def type_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /type Текст")
        return
    text = " ".join(context.args)
    await update.message.reply_text(f"⌨️ Печатаю: {text}")
    time.sleep(2)
    pyautogui.typewrite(text, interval=0.05)

# /paste — вставляет текст в буфер обмена
async def paste_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /paste Текст")
        return
    text = " ".join(context.args)
    pyperclip.copy(text)
    await update.message.reply_text("✅ Текст скопирован в буфер обмена")

# /beep — звуковой сигнал
async def beep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    import winsound
    winsound.Beep(1000, 500)
    await update.message.reply_text("🔔 Бип!")

# /tts — озвучить текст
async def tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /tts Текст")
        return
    text = " ".join(context.args)
    def speak():
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=speak).start()
    await update.message.reply_text(f"🔊 Озвучиваю: {text}")

# /meme — случайный мем с Reddit
async def meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    try:
        r = requests.get("https://meme-api.com/gimme", timeout=5).json()
        await update.message.reply_photo(photo=r["url"], caption=r["title"])
    except:
        await update.message.reply_text("❌ Не удалось загрузить мем")

# /weather — погода
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    city = " ".join(context.args) if context.args else "Birobidzhan"
    try:
        r = requests.get(f"https://wttr.in/{city}?format=3", timeout=5)
        await update.message.reply_text(f"🌤 {r.text}")
    except:
        await update.message.reply_text("❌ Не удалось получить погоду")

# /timer — таймер
async def timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /timer 60 (секунды)")
        return
    try:
        seconds = int(context.args[0])
        await update.message.reply_text(f"⏱ Таймер на {seconds} сек запущен!")
        async def send_alert():
            await asyncio.sleep(seconds)
            await update.message.reply_text("⏰ Таймер сработал!")
        asyncio.create_task(send_alert())
    except:
        await update.message.reply_text("❌ Укажи число секунд")




# Mute / Unmute
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    os.system("powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]173)")
    await update.message.reply_text("🔇 Звук выключен")



async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    os.system("powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]173)")
    await update.message.reply_text("🔊 Звук включён")



async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    os.system("rundll32.exe user32.dll,LockWorkStation")
    await update.message.reply_text("🔒 Экран заблокирован")

# /getclipboard — показать буфер обмена
async def get_clipboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    try:
        text = pyperclip.paste()
        if text:
            await update.message.reply_text(f"📋 Буфер обмена:\n\n{text}")
        else:
            await update.message.reply_text("📋 Буфер обмена пуст")
    except:
        await update.message.reply_text("❌ Не удалось получить буфер обмена")

# /remind — напоминание через N минут
async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /remind 30 Позвонить маме")
        return
    try:
        minutes = int(context.args[0])
        text = " ".join(context.args[1:])
        await update.message.reply_text(f"⏰ Напомню через {minutes} мин: {text}")
        async def send_reminder():
            await asyncio.sleep(minutes * 60)
            await update.message.reply_text(f"🔔 Напоминание: {text}")
        asyncio.create_task(send_reminder())
    except:
        await update.message.reply_text("❌ Укажи число минут и текст")



async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /block 123456789")
        return
    try:
        user_id = int(context.args[0])
        BLOCKED_USERS.add(user_id)
        save_blocked()
        await update.message.reply_text(f"🚫 Пользователь {user_id} заблокирован")
    except:
        await update.message.reply_text("❌ Укажи числовой ID")

# Обнови unblock_user
async def unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /unblock 123456789")
        return
    try:
        user_id = int(context.args[0])
        BLOCKED_USERS.discard(user_id)
        save_blocked()
        await update.message.reply_text(f"✅ Пользователь {user_id} разблокирован")
    except:
        await update.message.reply_text("❌ Укажи числовой ID")

        
async def block_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not BLOCKED_USERS:
        await update.message.reply_text("Список заблокированных пуст")
        return
    text = "\n".join([str(uid) for uid in BLOCKED_USERS])
    await update.message.reply_text(f"🚫 Заблокированные:\n{text}")

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /ai вопрос")
        return

    user_text = " ".join(context.args)
    groq_history.append({"role": "user", "content": user_text})
    await update.message.reply_text("🤔 Думаю...")

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": "You are a helpful assistant."}] + groq_history,
                "max_tokens": 1024
            },
            timeout=15
        )
        data = r.json()
        print("Groq ответ:", data)

        reply = data["choices"][0]["message"]["content"]
        print("Ответ получен:", repr(reply))

        groq_history.append({"role": "assistant", "content": reply})

        try:
            save_groq_history()
            print("История сохранена")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

        await update.message.reply_text(f"🤖 {reply}")
        print("Сообщение отправлено")

    except Exception as e:
        if groq_history:
            groq_history.pop()
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def clear_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    groq_history.clear()
    save_groq_history()
    await update.message.reply_text("🗑 История диалога очищена")


async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    if not context.args:
        await update.message.reply_text("Использование: /image кот в космосе")
        return
    
    prompt = " ".join(context.args)
    await update.message.reply_text("🎨 Генерирую изображение, подожди...")
    
    try:
        # Переводим промпт на английский через Groq
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "Translate the user's text to English for an image generation prompt. Return only the translated prompt, nothing else."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200
            },
            timeout=10
        )
        english_prompt = r.json()["choices"][0]["message"]["content"]
        print(f"Переведено: {english_prompt}")

        # Генерируем изображение
        image = hf_client.text_to_image(
    english_prompt,
    model="black-forest-labs/FLUX.1-schnell"
)
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        await update.message.reply_photo(photo=buf, caption=f"🎨 {prompt}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    text = """
🖥 *Команды бота "Связь с Никитой":*

*Управление ПК:*
/shutdown — выключить компьютер
/restart — перезагрузить компьютер
/sleep — спящий режим
/mute — выключить звук
/unmute — включить звук
/volume [0-100] — установить громкость
/alarm [текст] — громкое уведомление на ПК
/type [текст] — напечатать текст на ПК
/paste [текст] — скопировать текст в буфер обмена
/beep — звуковой сигнал
/tts [текст] — озвучить текст через динамики
/getclipboard — показать содержимое буфера обмена

*Мониторинг:*
/status — CPU, RAM, диск, батарея
/ip — внешний IP адрес

*Экран:*
/screenshot — скриншот экрана
/record [сек] — запись экрана (макс 60 сек)
/lock — заблокировать экран

*Браузер:*
/open [ссылка] — открыть ссылку в браузере

*Уведомления:*
/notify [текст] — показать уведомление на экране ПК
/remind [мин] [текст] — напоминание через N минут в Telegram

*Сообщения:*
/send [имя или id] [текст] — отправить сообщение
/heart — отправить ❤️❤️❤️ заданному пользователю
/block [id] — заблокировать пользователя
/unblock [id] — разблокировать пользователя
/blocklist — список заблокированных

*рофлес:*
/meme — случайный мем
/coin — подбросить монетку
/8ball [вопрос] — магический шар
/weather [город] — погода
/timer [секунды] — таймер с уведомлением

*ИИ Ассистент:*
/ai [вопрос] — спросить ИИ ассистента
/clearai — сбросить историю диалога с ИИ
/image [описание] — сгенерировать изображение по описанию

/help — это сообщение
    """
    await update.message.reply_text(text, parse_mode="Markdown")
    

HEART_USER_ID = 5215525886  # вставь нужный ID

async def heart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_access(update): return
    await context.bot.send_message(chat_id=HEART_USER_ID, text="❤️❤️❤️")
    await update.message.reply_text("❤️ Отправлено!")






app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("lock", lock))
app.add_handler(CommandHandler("getclipboard", get_clipboard))
app.add_handler(CommandHandler("remind", remind))
app.add_handler(CommandHandler("shutdown", shutdown))
app.add_handler(CommandHandler("restart", restart))
app.add_handler(CommandHandler("screenshot", screenshot))
app.add_handler(CommandHandler("record", record))
app.add_handler(CommandHandler("open", openurl))
app.add_handler(CommandHandler("send", send_msg))
app.add_handler(CommandHandler("heart", heart))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("notify", notify))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("ip", get_ip))
app.add_handler(CommandHandler("sleep", sleep_pc))
app.add_handler(CommandHandler("volume", volume))
app.add_handler(CommandHandler("mute", mute))
app.add_handler(CommandHandler("unmute", unmute))
app.add_handler(CommandHandler("coin", coin))
app.add_handler(CommandHandler("8ball", eightball))
app.add_handler(CommandHandler("alarm", alarm))
app.add_handler(CommandHandler("type", type_text))
app.add_handler(CommandHandler("paste", paste_text))
app.add_handler(CommandHandler("beep", beep))
app.add_handler(CommandHandler("tts", tts))
app.add_handler(CommandHandler("meme", meme))
app.add_handler(CommandHandler("weather", weather))
app.add_handler(CommandHandler("timer", timer))
app.add_handler(CommandHandler("block", block_user))
app.add_handler(CommandHandler("unblock", unblock_user))
app.add_handler(CommandHandler("blocklist", block_list))
app.add_handler(CommandHandler("ai", ai_chat))
app.add_handler(CommandHandler("clear", clear_ai))
app.add_handler(CommandHandler("image", generate_image))


# Этот хэндлер ОБЯЗАТЕЛЬНО последним:
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_to_owner))

app.run_polling()
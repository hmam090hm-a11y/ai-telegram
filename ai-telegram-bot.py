#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, asyncio, logging, requests, tempfile
from collections import defaultdict, deque
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler, ContextTypes, filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN or not WEBHOOK_URL:
    raise RuntimeError("❌ BOT_TOKEN أو WEBHOOK_URL غير موجود")

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else None
logging.basicConfig(level=logging.INFO)

# ================= MODELS =================
MODELS = {
    "flan": ("⚡ Flan-T5", "https://api-inference.huggingface.co/models/google/flan-t5-base"),
    "gpt2": ("💬 DistilGPT2", "https://api-inference.huggingface.co/models/distilgpt2"),
    "bart": ("🧠 BART", "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"),
}

# ================= STATE =================
user_model = defaultdict(lambda: "flan")
user_voice = defaultdict(bool)
user_last = defaultdict(float)
user_memory = defaultdict(lambda: deque(maxlen=6))
CACHE = {}
RATE_LIMIT = 3

# ================= AI =================
def ask_ai(prompt, model_key):
    name, url = MODELS[model_key]
    try:
        r = requests.post(url, headers=HEADERS, json={"inputs": prompt}, timeout=12)
        if r.status_code != 200:
            raise Exception("fail")
        data = r.json()
        if isinstance(data, list):
            return data[0].get("generated_text", "")
    except:
        return None
    return None

def smart_ai(prompt):
    for k in MODELS:
        res = ask_ai(prompt, k)
        if res:
            return res
    return fallback(prompt)

def fallback(text):
    if "اخر المخلوقات" in text:
        return "آخر المخلوقات موتًا هو ملك الموت بعد قبض أرواح الخلق."
    return "⚠️ الذكاء الاصطناعي مشغول حالياً، حاول لاحقاً."

# ================= TTS =================
def tts(text):
    try:
        from gtts import gTTS
        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        gTTS(text=text, lang="ar").save(fp.name)
        return fp.name
    except:
        return None

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 بوت ذكاء اصطناعي خارق\n"
        "اكتب سؤالك مباشرة\n"
        "/model لتغيير الموديل"
    )

async def model_cmd(update, context):
    kb = [[InlineKeyboardButton(v[0], callback_data=k)] for k,v in MODELS.items()]
    await update.message.reply_text("اختر موديل:", reply_markup=InlineKeyboardMarkup(kb))

async def status(update, context):
    m = user_model[update.effective_user.id]
    v = "مفعّل" if user_voice[update.effective_user.id] else "مغلق"
    await update.message.reply_text(f"🧠 {MODELS[m][0]}\n🔊 الصوت: {v}")

async def reset(update, context):
    user_memory[update.effective_user.id].clear()
    await update.message.reply_text("🗑️ تم مسح الذاكرة")

async def voice(update, context):
    uid = update.effective_user.id
    if "on" in update.message.text:
        user_voice[uid] = True
        await update.message.reply_text("🔊 تم تفعيل الصوت")
    else:
        user_voice[uid] = False
        await update.message.reply_text("🔇 تم إيقاف الصوت")

async def model_select(update, context):
    q = update.callback_query
    await q.answer()
    user_model[q.from_user.id] = q.data
    await q.edit_message_text(f"✅ تم اختيار {MODELS[q.data][0]}")

# ================= CHAT =================
async def chat(update, context):
    uid = update.effective_user.id
    now = time.time()
    if now - user_last[uid] < RATE_LIMIT:
        await update.message.reply_text("⏳ انتظر قليلاً")
        return
    user_last[uid] = now

    text = update.message.text
    mem = "\n".join(user_memory[uid])
    prompt = mem + "\n" + text

    key = f"{user_model[uid]}:{prompt}"
    if key in CACHE:
        reply = CACHE[key]
    else:
        await update.message.reply_text("🤔 أفكر...")
        reply = await asyncio.get_event_loop().run_in_executor(None, smart_ai, prompt)
        CACHE[key] = reply

    user_memory[uid].append(text)
    user_memory[uid].append(reply)

    if user_voice[uid]:
        audio = tts(reply)
        if audio:
            await context.bot.send_voice(update.effective_chat.id, open(audio,"rb"))
            return

    await update.message.reply_text(reply)

# ================= WEBHOOK =================
async def webhook_handler(req):
    data = await req.json()
    upd = Update.de_json(data, app.bot)
    await app.update_queue.put(upd)
    return web.Response(text="ok")

async def startup(appx):
    await app.initialize()
    await app.start()
    await app.bot.set_webhook(WEBHOOK_URL)
    logging.info("🚀 Webhook Ready")

async def cleanup(appx):
    await app.stop()
    await app.shutdown()

# ================= MAIN =================
app: Application = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("model", model_cmd))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(CommandHandler("voice", voice))
app.add_handler(CallbackQueryHandler(model_select))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

web_app = web.Application()
web_app.router.add_post("/", webhook_handler)
web_app.on_startup.append(startup)
web_app.on_cleanup.append(cleanup)

if __name__ == "__main__":
    web.run_app(web_app, host="0.0.0.0", port=PORT)

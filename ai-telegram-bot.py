#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import aiohttp
from aiohttp import web

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# ================== ENV ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# تأكد من أن رابطك لا ينتهي بشرطة مائلة /
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")  # مثل https://ai-telegram-fvku.onrender.com
PORT = int(os.environ.get("PORT", 10000))

if not all([BOT_TOKEN, GROQ_API_KEY, WEBHOOK_URL]):
    raise RuntimeError("❌ تأكد من BOT_TOKEN / GROQ_API_KEY / WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== GROQ ==================
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

async def ask_ai(prompt: str) -> str:
    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 512,
    }
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(GROQ_URL, headers=HEADERS, json=payload) as r:
                if r.status != 200:
                    return "⚠️ حصل خطأ مؤقت، أعد المحاولة."
                data = await r.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return "⚠️ عذرًا، لم أستطع الحصول على إجابة الآن."

# ================== Telegram Handlers ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 بوت ذكاء صاروخي\nاكتب أي شيء.")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    await update.message.reply_text("⚡ أفكر...")
    reply = await ask_ai(msg)
    await update.message.reply_text(reply)

# ================== Webhook Server (مُصَحَّح) ==================
async def webhook_handler(request):
    """معالجة طلبات الويب هوك من تليجرام"""
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.update_queue.put(update)
    return web.Response(text="OK")

async def health_check(request):
    """للتحقق من أن الخادم يعمل"""
    return web.Response(text="🤖 البوت يعمل بنجاح!")

async def main():
    global telegram_app  # لجعل التطبيق متاحًا للويب هوك

    # 1. بناء تطبيق تليجرام
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    # 2. تهيئة التطبيق وضبط الويب هوك
    await telegram_app.initialize()
    # تأكد من أن المسار الصحيح هو /webhook بدون شرطة مائلة زائدة
    webhook_path = f"{WEBHOOK_URL}/webhook"
    await telegram_app.bot.set_webhook(url=webhook_path)
    logger.info(f"✅ تم تعيين Webhook على: {webhook_path}")
    await telegram_app.start()

    # 3. إنشاء تطبيق ويب aiohttp وإضافة المسارات
    web_app = web.Application()
    # المسار الرئيسي /webhook لاستقبال التحديثات من تليجرام
    web_app.router.add_post("/webhook", webhook_handler)
    # مسار للصفحة الرئيسية لفحص الحالة
    web_app.router.add_get("/", health_check)
    web_app.router.add_get("/health", health_check)

    # 4. تشغيل الخادم على المنفذ المحدد (مهم لـ Render)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"🚀 الخادم يعمل على المنفذ: {PORT}")
    logger.info(f"📱 يمكن فتح الرابط: {WEBHOOK_URL} للتحقق")

    # 5. الانتظار إلى الأبد (هذا يبقي الخادم نشطًا)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

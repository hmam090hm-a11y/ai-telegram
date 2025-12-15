#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import asyncio
import requests
from aiohttp import web

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== الإعدادات ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # اختياري

if not BOT_TOKEN or not HF_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN أو HF_TOKEN غير موجود")

HF_API_URL = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

logging.basicConfig(level=logging.INFO)

# ================== AI ==================
def ask_ai(text: str) -> str:
    try:
        payload = {"inputs": text}
        r = requests.post(
            HF_API_URL,
            headers=HEADERS,
            json=payload,
            timeout=90
        )

        if r.status_code != 200:
            return "❌ الذكاء الاصطناعي مشغول حالياً"

        data = r.json()
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "❌ لا يوجد رد")
        return "❌ لا يوجد رد"

    except Exception as e:
        logging.error(e)
        return "❌ خطأ في الاتصال بالذكاء الاصطناعي"

# ================== Handlers ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 بوت ذكاء اصطناعي\n"
        "✍️ اكتب سؤالك وسأجيبك"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ أفكر...")
    reply = ask_ai(update.message.text)
    await update.message.reply_text(reply)

# ================== التشغيل ==================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await app.initialize()
    await app.start()

    # ================== Webhook ==================
    if WEBHOOK_URL:
        logging.info("🚀 تشغيل Webhook")

        await app.bot.set_webhook(WEBHOOK_URL)

        async def handle(request):
            data = await request.json()
            update = Update.de_json(data, app.bot)
            await app.update_queue.put(update)
            return web.Response(text="ok")

        web_app = web.Application()
        web_app.router.add_post("/", handle)

        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(
            runner,
            "0.0.0.0",
            int(os.getenv("PORT", "10000"))
        )
        await site.start()

        while True:
            await asyncio.sleep(3600)

    # ================== Polling ==================
    else:
        logging.info("🟢 تشغيل Polling")
        await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

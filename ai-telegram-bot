
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Free AI Telegram Bot

Chat only

Arabic + English

Uses HuggingFace Inference API (FREE)

Webhook (Render compatible) """


import os import asyncio import logging from aiohttp import web import nest_asyncio import requests

from telegram import Update from telegram.ext import ( ApplicationBuilder, MessageHandler, ContextTypes, filters, )

================== CONFIG ==================

BOT_TOKEN = os.getenv("BOT_TOKEN") HF_TOKEN = os.getenv("HF_TOKEN") WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://xxxx.onrender.com/ PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN or not HF_TOKEN or not WEBHOOK_URL: raise RuntimeError("Set BOT_TOKEN, HF_TOKEN, WEBHOOK_URL")

HF_MODEL = "tiiuae/falcon-7b-instruct"  # جيد للعربي + الانجليزي HF_API = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

HEADERS = { "Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json", }

logging.basicConfig(level=logging.INFO)

================== AI ==================

def ai_reply(prompt: str) -> str: payload = { "inputs": prompt, "parameters": { "max_new_tokens": 300, "temperature": 0.7, "return_full_text": False, } } try: r = requests.post(HF_API, headers=HEADERS, json=payload, timeout=60) r.raise_for_status() data = r.json() if isinstance(data, list) and data: return data[0].get("generated_text", "❌ لم أستطع الرد") return "❌ رد غير متوقع" except Exception as e: return f"❌ خطأ: {e}"

================== HANDLERS ==================

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): text = (update.message.text or "").strip() if not text: return

await update.message.reply_text("🤖 أفكر...")

loop = asyncio.get_event_loop()
reply = await loop.run_in_executor(None, ai_reply, text)

await update.message.reply_text(reply)

================== WEBHOOK ==================

def main(): nest_asyncio.apply()

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

async def tg_webhook(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.update_queue.put(update)
    return web.Response(text="ok")

web_app = web.Application()
web_app.router.add_post("/", tg_webhook)

async def run():
    await app.initialize()
    await app.start()
    await app.bot.set_webhook(WEBHOOK_URL)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logging.info("🚀 AI Bot Running (FREE)")
    while True:
        await asyncio.sleep(3600)

asyncio.run(run())

if name == "main": main()

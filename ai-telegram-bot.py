#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== إعدادات ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN or not GROQ_API_KEY or not WEBHOOK_URL:
    raise RuntimeError("❌ متغيرات ناقصة")

logging.basicConfig(level=logging.INFO)

# ================== Groq ==================
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def ask_ai(prompt: str) -> str:
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "أجب بالعربية بوضوح وبدون حشو."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.5,
        "max_tokens": 600
    }

    r = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json=payload,
        timeout=8
    )

    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]

    return "لم أفهم سؤالك، وضحه أكثر."

# ================== Handlers ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 بوت ذكاء اصطناعي سريع جدًا ⚡\n\n"
        "✍️ اكتب سؤالك مباشرة."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    thinking = await update.message.reply_text("⚡ ...")

    reply = ask_ai(user_text)
    await thinking.edit_text(reply)

# ================== Webhook ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    async def run():
        await app.initialize()
        await app.bot.set_webhook(WEBHOOK_URL)
        await app.start()

        logging.info("🚀 Bot is LIVE")

        while True:
            await asyncio.sleep(3600)

    asyncio.run(run())

if __name__ == "__main__":
    main()

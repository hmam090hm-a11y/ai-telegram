#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
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

# ================== الإعدادات ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")      # توكن البوت
HF_TOKEN = os.getenv("HF_TOKEN")        # توكن HuggingFace

if not BOT_TOKEN or not HF_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN أو HF_TOKEN غير موجود")

HF_API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

logging.basicConfig(level=logging.INFO)

# ================== الذكاء الاصطناعي ==================
def ask_ai(text: str) -> str:
    payload = {"inputs": text}
    r = requests.post(HF_API_URL, headers=HEADERS, json=payload, timeout=60)

    if r.status_code != 200:
        return "❌ خطأ من خادم الذكاء الاصطناعي"

    data = r.json()
    if isinstance(data, list):
        return data[0].get("generated_text", "❌ لا يوجد رد")
    return "❌ لا يوجد رد"

# ================== Handlers ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 أهلاً بك في بوت الذكاء الاصطناعي\n\n"
        "✍️ اكتب أي سؤال أو طلب وسأرد عليك."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("⏳ أفكر...")

    reply = ask_ai(user_text)
    await update.message.reply_text(reply)

# ================== تشغيل البوت ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 AI Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

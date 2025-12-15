#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import aiohttp
from aiohttp import web

from telegram import Update
from telegram.ext import (
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

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================== GROQ ==================
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

async def ask_ai(prompt: str) -> str:
    """استدعاء واجهة Groq API مع تسجيل الأخطاء المفصل"""
    # جرب هذا النموذج أولاً (أبسط وأسرع)
    payload = {
        "model": "llama3-8b-8192",  # تم التغيير إلى نموذج أبسط للتجربة
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 512,
    }
    
    try:
        logger.info(f"📤 إرسال طلب إلى Groq API...")
        logger.info(f"   النموذج: {payload['model']}")
        logger.info(f"   الرسالة: {prompt[:50]}...")  # أول 50 حرف فقط
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(GROQ_URL, headers=HEADERS, json=payload) as response:
                
                # تسجيل حالة الاستجابة
                status_code = response.status
                logger.info(f"📥 حالة الاستجابة: {status_code}")
                
                # قراءة نص الاستجابة
                response_text = await response.text()
                
                if status_code != 200:
                    # تسجيل الخطأ المفصل
                    logger.error(f"❌ خطأ Groq API:")
                    logger.error(f"   الكود: {status_code}")
                    logger.error(f"   النص: {response_text[:500]}")  # أول 500 حرف فقط
                    
                    # إعادة رسالة أكثر وضوحاً للمستخدم
                    if status_code == 401:
                        return "🔐 خطأ في مفتاح API. تحقق من GROQ_API_KEY في إعدادات Render."
                    elif status_code == 429:
                        return "⏳ تجاوزت الحد المسموح لطلبات API. حاول مرة أخرى لاحقاً."
                    elif status_code == 404:
                        return f"🔍 النموذج '{payload['model']}' غير موجود. جرب نموذجاً آخر."
                    else:
                        return f"⚠️ خطأ من خادم Groq (الكود: {status_code}). حاول مرة أخرى."
                
                # إذا كانت الاستجابة ناجحة
                logger.info("✅ استجابة ناجحة من Groq API")
                data = await response.json()
                answer = data["choices"][0]["message"]["content"]
                logger.info(f"📝 طول الإجابة: {len(answer)} حرف")
                logger.info(f"📝 الإجابة (50 حرف): {answer[:50]}...")
                return answer
                
    except asyncio.TimeoutError:
        logger.error("⏱️ انتهت مهلة الاتصال بـ Groq API (30 ثانية)")
        return "⏱️ تجاوز الوقت المسموح للاتصال بالخادم."
    except Exception as e:
        logger.error(f"💥 خطأ غير متوقع: {str(e)}")
        return "💥 حدث خطأ غير متوقع. حاول مرة أخرى."

# ================== Telegram Handlers ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    welcome_text = """
🚀 أهلاً! أنا بوت الذكاء الاصطناعي

أستطيع مساعدتك في:
• الإجابة على أسئلتك
• المساعدة في الكتابة
• شرح المفاهيم
• الترجمة
• وأكثر...

ما الذي تريد معرفته؟
    """
    await update.message.reply_text(welcome_text)

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل النصية"""
    user_message = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or "مستخدم"
    
    logger.info(f"💬 رسالة من @{username} (ID: {user_id}): {user_message[:50]}...")
    
    # إرسال رسالة "جاري التفكير"
    thinking_msg = await update.message.reply_text("🤔 جاري التفكير في سؤالك...")
    
    try:
        # الحصول على الرد من الذكاء الاصطناعي
        ai_response = await ask_ai(user_message)
        
        # حذف رسالة "جاري التفكير"
        await thinking_msg.delete()
        
        # إرسال الرد (بتقسيمه إذا كان طويلاً)
        if len(ai_response) > 4000:
            # تقسيم الرسالة الطويلة
            for i in range(0, len(ai_response), 4000):
                part_num = i // 4000 + 1
                await update.message.reply_text(f"📄 الجزء {part_num}:\n{ai_response[i:i+4000]}")
        else:
            await update.message.reply_text(ai_response)
            
        logger.info(f"✅ تم الرد على @{username}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الرسالة: {str(e)}")
        await update.message.reply_text("❌ حدث خطأ أثناء المعالجة، يرجى المحاولة مرة أخرى.")

# ================== Webhook Server ==================
async def webhook_handler(request):
    """معالجة طلبات الويب هوك من تليجرام"""
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.update_queue.put(update)
        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return web.Response(text="Error", status=500)

async def health_check(request):
    """للتحقق من أن الخادم يعمل"""
    return web.Response(text="🤖 البوت يعمل بنجاح!\nرابط: https://ai-telegram-fvku.onrender.com\nWebhook: /webhook")

async def main():
    global telegram_app
    
    # 1. بناء تطبيق تليجرام
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    
    # 2. تهيئة التطبيق وضبط الويب هوك
    await telegram_app.initialize()
    webhook_path = f"{WEBHOOK_URL}/webhook"
    await telegram_app.bot.set_webhook(url=webhook_path)
    logger.info(f"✅ تم تعيين Webhook على: {webhook_path}")
    await telegram_app.start()
    
    # 3. إنشاء تطبيق ويب aiohttp
    web_app = web.Application()
    web_app.router.add_post("/webhook", webhook_handler)
    web_app.router.add_get("/", health_check)
    web_app.router.add_get("/health", health_check)
    
    # 4. تشغيل الخادم
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    logger.info(f"🚀 الخادم يعمل على المنفذ: {PORT}")
    logger.info(f"📱 رابط البوت: {WEBHOOK_URL}")
    logger.info(f"🤖 اسم البوت: @{(await telegram_app.bot.get_me()).username}")
    logger.info("✅ البوت جاهز للاستخدام!")
    logger.info("📝 أرسل /start في Telegram للبدء")
    
    # 5. الانتظار إلى الأبد
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import aiohttp
import json
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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")
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
    """استدعاء واجهة Groq API مع تسجيل مفصل"""
    # تنظيف وتجهيز النص
    if not prompt or not prompt.strip():
        return "الرجاء إدخال رسالة نصية."
    
    cleaned_prompt = prompt.strip()
    
    # payload مبسط وصحيح للتجربة
    payload = {
        "model": "llama3.1-8b-instant",  # نموذج مضمون العمل
        "messages": [
            {
                "role": "user", 
                "content": cleaned_prompt[:2000]  # قص النص إذا كان طويلاً
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 1,
        "stream": False
    }
    
    try:
        # تسجيل payload المرسل
        logger.info(f"📤 إرسال طلب إلى Groq API:")
        logger.info(f"   النموذج: {payload['model']}")
        logger.info(f"   طول الرسالة: {len(cleaned_prompt)} حرف")
        logger.info(f"   أول 100 حرف: {cleaned_prompt[:100]}")
        
        # إرسال الطلب
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(GROQ_URL, headers=HEADERS, json=payload) as response:
                
                status_code = response.status
                response_text = await response.text()
                
                logger.info(f"📥 حالة الاستجابة: {status_code}")
                
                # إذا كان هناك خطأ
                if status_code != 200:
                    logger.error("=" * 50)
                    logger.error(f"❌ خطأ من Groq API")
                    logger.error(f"   الكود: {status_code}")
                    logger.error(f"   الاستجابة الكاملة: {response_text}")
                    logger.error("=" * 50)
                    
                    # رسائل محددة لكل نوع خطأ
                    if status_code == 400:
                        # محاولة فهم سبب الخطأ 400
                        try:
                            error_data = json.loads(response_text)
                            error_msg = error_data.get("error", {}).get("message", "طلب غير صحيح")
                            logger.error(f"   رسالة الخطأ: {error_msg}")
                            return f"📝 خطأ في الطلب: {error_msg}"
                        except:
                            return "📝 خطأ في تنسيق الطلب. جرب كتابة رسالة أخرى."
                    
                    elif status_code == 401:
                        return "🔐 خطأ في مفتاح API. تحقق من GROQ_API_KEY في Render."
                    
                    elif status_code == 429:
                        return "⏳ تجاوزت الحد المسموح. حاول مرة أخرى لاحقاً."
                    
                    else:
                        return f"⚠️ خطأ من الخادم (كود: {status_code}). حاول مرة أخرى."
                
                # إذا كانت الاستجابة ناجحة
                logger.info("✅ استجابة ناجحة من Groq API")
                
                try:
                    data = json.loads(response_text)
                    answer = data["choices"][0]["message"]["content"]
                    logger.info(f"📝 تم استلام إجابة طولها {len(answer)} حرف")
                    return answer
                except Exception as e:
                    logger.error(f"❌ خطأ في تحليل الاستجابة: {str(e)}")
                    return "⚠️ حصل خطأ في معالجة الرد."
                
    except asyncio.TimeoutError:
        logger.error("⏱️ انتهت مهلة الاتصال بـ Groq API")
        return "⏱️ تجاوز الوقت المسموح للاتصال."
    
    except Exception as e:
        logger.error(f"💥 خطأ غير متوقع: {str(e)}")
        return "💥 حدث خطأ غير متوقع. حاول مرة أخرى."

# ================== Telegram Handlers ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    welcome_text = """
🚀 أهلاً وسهلاً! 

أنا بوت الذكاء الاصطناعي المُساعد.

• اسألني أي سؤال
• اطلب مني المساعدة في الكتابة
• أو مجرد تحديق!

اكتب رسالتك وسأرد عليك فوراً.
    """
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /help"""
    help_text = """
📚 **الأوامر المتاحة:**

/start - بدء التشغيل وعرض الترحيب
/help - عرض هذه الرسالة
/test - اختبار اتصال البوت

💬 **كيفية الاستخدام:**
ما عليك سوى كتابة رسالتك وسأرد عليك!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختبار اتصال البوت"""
    await update.message.reply_text("✅ البوت يعمل بشكل طبيعي!\nجرب كتابة 'مرحباً'")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل النصية"""
    user_message = update.message.text
    
    # تجاهل الأوامر (تم التعامل معها بواسطة command handlers)
    if user_message.startswith('/'):
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    
    logger.info(f"💬 رسالة من @{username}: {user_message[:50]}...")
    
    # إرسال رسالة "جاري المعالجة"
    thinking_msg = await update.message.reply_text("⏳ جاري معالجة طلبك...")
    
    try:
        # الحصول على الرد من الذكاء الاصطناعي
        ai_response = await ask_ai(user_message)
        
        # حذف رسالة الانتظار
        await thinking_msg.delete()
        
        # إرسال الرد
        await update.message.reply_text(ai_response)
        
        logger.info(f"✅ تم الرد على @{username}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الرسالة: {str(e)}")
        await update.message.reply_text("❌ حدث خطأ أثناء المعالجة.")

# ================== Webhook Server ==================
telegram_app = None

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
    return web.Response(text="🤖 البوت يعمل بنجاح!\n\nرابط الخدمة: https://ai-telegram-fvku.onrender.com\nWebhook: /webhook\nالمنفذ: 10000")

async def main():
    global telegram_app
    
    # 1. بناء تطبيق تليجرام
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("test", test_command))
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
    
    logger.info("=" * 50)
    logger.info(f"🚀 الخادم يعمل على المنفذ: {PORT}")
    logger.info(f"📱 رابط الويب: {WEBHOOK_URL}")
    logger.info(f"🔗 Webhook: {webhook_path}")
    logger.info("✅ البوت جاهز للاستخدام!")
    logger.info("=" * 50)
    
    # 5. إبقاء الخادم نشطاً
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

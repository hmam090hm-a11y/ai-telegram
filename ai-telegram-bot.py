#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import aiohttp
from aiohttp import web
import signal

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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # مثال: https://your-bot.onrender.com
PORT = int(os.environ.get("PORT", 10000))

# التحقق من المتغيرات البيئية
REQUIRED_ENV = {
    "BOT_TOKEN": BOT_TOKEN,
    "GROQ_API_KEY": GROQ_API_KEY,
    "WEBHOOK_URL": WEBHOOK_URL,
}

missing_vars = [key for key, value in REQUIRED_ENV.items() if not value]
if missing_vars:
    raise RuntimeError(f"❌ المتغيرات البيئية المفقودة: {', '.join(missing_vars)}")

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================== GROQ API ==================
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}

async def ask_ai(prompt: str) -> str:
    """استدعاء واجهة Groq API"""
    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 512,
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(GROQ_URL, headers=HEADERS, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Groq API error: {response.status} - {error_text}")
                    return "⚠️ حدث خطأ في الخدمة، يرجى المحاولة مرة أخرى لاحقًا."
                
                data = await response.json()
                return data["choices"][0]["message"]["content"].strip()
                
    except asyncio.TimeoutError:
        logger.error("Groq API timeout")
        return "⏱️ تجاوز الوقت المسموح، يرجى المحاولة مرة أخرى."
    except Exception as e:
        logger.error(f"Groq API exception: {str(e)}")
        return "⚠️ حدث خطأ غير متوقع، يرجى المحاولة مرة أخرى."

# ================== Telegram Handlers ==================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    welcome_text = """
مرحباً! 🤖

أنا بوت ذكي يمكنني مساعدتك في:
- الإجابة على أسئلتك
- المساعدة في الكتابة
- شرح المفاهيم
- وأكثر...

ما الذي تريد معرفته اليوم؟
"""
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /help"""
    help_text = """
📚 **أوامر البوت:**
/start - بدء التشغيل
/help - عرض هذه المساعدة
/about - معلومات عن البوت

💬 **طريقة الاستخدام:**
ما عليك سوى كتابة رسالتك وسأرد عليك فوراً!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /about"""
    about_text = """
🤖 **معلومات البوت:**
- الاسم: بوت الذكاء الاصطناعي
- النظام: Groq API + Llama 3
- المطور: @username
- الإصدار: 1.0

🔥 مدعوم بتقنيات الذكاء الاصطناعي المتقدمة
"""
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل النصية"""
    user_message = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or "غير معروف"
    
    logger.info(f"رسالة من {username} ({user_id}): {user_message[:50]}...")
    
    # إرسال حالة التفكير
    thinking_msg = await update.message.reply_text("🤔 جاري التفكير...")
    
    try:
        # الحصول على الرد من الذكاء الاصطناعي
        ai_response = await ask_ai(user_message)
        
        # حذف رسالة "جاري التفكير"
        await thinking_msg.delete()
        
        # إرسال الرد (بتقسيمه إذا كان طويلاً)
        if len(ai_response) > 4000:
            for i in range(0, len(ai_response), 4000):
                await update.message.reply_text(ai_response[i:i+4000])
        else:
            await update.message.reply_text(ai_response)
            
        logger.info(f"تم الرد على {username}")
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الرسالة: {str(e)}")
        await update.message.reply_text("❌ حدث خطأ أثناء المعالجة، يرجى المحاولة مرة أخرى.")

# ================== Webhook Server ==================
async def webhook_handler(request):
    """معالج Webhook"""
    try:
        # قراءة البيانات من الطلب
        data = await request.json()
        
        # تحويل JSON إلى كائن Update
        update = Update.de_json(data, telegram_bot.bot)
        
        # وضع Update في الطابور
        await telegram_bot.update_queue.put(update)
        
        return web.Response(text="OK", status=200)
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return web.Response(text="Error", status=500)

async def health_check(request):
    """فحص صحة الخادم"""
    return web.Response(text="🚀 البوت يعمل بنجاح!", status=200)

async def setup_application():
    """إعداد تطبيق البوت"""
    # إنشاء تطبيق Telegram
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    
    # تهيئة التطبيق
    await app.initialize()
    
    # تعيين Webhook
    webhook_url = f"{WEBHOOK_URL}/webhook"
    await app.bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True
    )
    
    logger.info(f"✅ تم تعيين Webhook على: {webhook_url}")
    
    # بدء التطبيق
    await app.start()
    
    return app

async def start_server():
    """بدء خادم الويب"""
    # إعداد تطبيق Telegram
    global telegram_bot
    telegram_bot = await setup_application()
    
    # إنشاء تطبيق الويب
    web_app = web.Application()
    
    # إضافة المسارات
    web_app.router.add_post("/webhook", webhook_handler)
    web_app.router.add_get("/", health_check)
    web_app.router.add_get("/health", health_check)
    
    # بدء الخادم
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    # التأكد من أن PORT تم تعيينه بشكل صحيح
    actual_port = PORT
    if actual_port is None:
        actual_port = 10000
        logger.warning(f"PORT غير محدد، استخدام المنفذ الافتراضي: {actual_port}")
    
    site = web.TCPSite(runner, "0.0.0.0", actual_port)
    await site.start()
    
    logger.info(f"🚀 الخادم يعمل على: http://0.0.0.0:{actual_port}")
    logger.info(f"📱 Webhook URL: {WEBHOOK_URL}/webhook")
    logger.info(f"🤖 البوت: @{(await telegram_bot.bot.get_me()).username}")
    logger.info("✅ البوت جاهز للاستخدام!")
    
    return runner, telegram_bot

async def shutdown(telegram_app, web_runner):
    """إيقاف الخادم والتطبيق"""
    logger.info("⏳ جاري الإيقاف...")
    
    # إيقاف Telegram bot
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()
    
    # إيقاف خادم الويب
    if web_runner:
        await web_runner.cleanup()
    
    logger.info("✅ تم الإيقاف بنجاح")

def main():
    """الدالة الرئيسية"""
    # إعدادات التعامل مع إشارات النظام
    loop = asyncio.get_event_loop()
    
    # متغيرات لحفظ حالات الخادم
    web_runner = None
    telegram_app = None
    
    async def start_all():
        nonlocal web_runner, telegram_app
        web_runner, telegram_app = await start_server()
        return web_runner, telegram_app
    
    async def stop_all():
        await shutdown(telegram_app, web_runner)
    
    # بدء التشغيل
    try:
        web_runner, telegram_app = loop.run_until_complete(start_all())
        
        # الانتظار إلى الأبد
        loop.run_forever()
        
    except KeyboardInterrupt:
        logger.info("📴 تم استقبال إشارة الإيقاف...")
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {str(e)}")
    finally:
        # الإيقاف النظيف
        loop.run_until_complete(stop_all())
        loop.close()

if __name__ == "__main__":
    main()

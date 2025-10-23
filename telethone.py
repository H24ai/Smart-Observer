"""
سكربت لمراقبة المجموعات عن كلمات مفتاحية معينة وإرسال إشعار مفصل إلى قناة خاصة.
"""

import os
import re
import asyncio
import requests
from telethon import TelegramClient, events
from telethon.errors import rpcerrorlist

# -----------------------------------------------------------------------------
#  قسم الإعدادات الرئيسية (ما تحتاج إلى تعديله)
# -----------------------------------------------------------------------------

# !!! هام: ضع معرف القناة الرقمي الخاص الذي تريد استقبال الإشعارات فيه !!!
# يجب أن يكون رقماً (وليس رابطاً)، ويبدأ بـ -100 للمجموعات والقنوات الخاصة.
# مثال: TARGET_CHANNEL_ID = -1001234567890
TARGET_CHANNEL_ID = -1003189190833  # <--- ضع المعرف هنا

# --- كلمات البحث (عدّلها حسب حاجتك) ---
KEYWORDS = [
    'يحل','يسوي','احتاج','يمسك','يحضر','يتابع','يسجل',
    'سكليف','مشروع','يساعد','تسوي','تحل','يتدرب عني',
    'يطبق عني','يضبطني','يضبطنا','عندي تطبيق','كيف اطبق',
    'احتاج احد','يصمم','يعلمني','ثقه','مضمون','يدرس','يختبر',
    'يمسك مواد','يشتغل','يضبط','يفهم','فاهم','يحلون','يسوون',
    'يساعدني','عذر طبي','عذر'
]
# تجاهل حالة الأحرف (True) أو مطابقتها (False)
IGNORE_CASE = True

# -----------------------------------------------------------------------------
#  (لا تقم بالتعديل هنا إلا إذا كنت تعرف ماذا تفعل)
# -----------------------------------------------------------------------------

# --- إعدادات الاتصال بتيليجرام ---
def get_env_or_prompt(name, prompt_text):
    val = os.getenv(name)
    if val:
        return val
    return input(f"{prompt_text}: ").strip()

API_ID_str = get_env_or_prompt("TG_API_ID", "أدخل API_ID (من my.telegram.org)")
API_HASH = get_env_or_prompt("TG_API_HASH", "أدخل API_HASH (من my.telegram.org)")
BOT_TOKEN = get_env_or_prompt("BOT_TOKEN", "أدخل BOT_TOKEN (من BotFather)")
SESSION_NAME = os.getenv("TG_SESSION", "watcher_session")

try:
    API_ID = int(API_ID_str)
except (ValueError, TypeError):
    raise SystemExit("خطأ: API_ID يجب أن يكون رقماً.")

if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise SystemExit("خطأ: يجب توفير API_ID, API_HASH, و BOT_TOKEN.")

if not TARGET_CHANNEL_ID:
    print("تحذير: المتغير 'TARGET_CHANNEL_ID' غير معين في الكود.")
    print("الرجاء تعديل الملف ووضع معرف القناة الرقمي الصحيح.")

# --- تجهيز أنماط البحث (Regex) ---
flags = re.IGNORECASE if IGNORE_CASE else 0
PATTERNS = [re.compile(kw.strip(), flags) for kw in KEYWORDS if kw and kw.strip()]

if not PATTERNS:
    print("تحذير: قائمة الكلمات المفتاحية فارغة، لن يتم رصد أي شيء.")

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

def matches_any(text: str) -> bool:
    """يتحقق مما إذا كان النص يطابق أياً من الأنماط المحددة."""
    if not text:
        return False
    return any(p.search(text) for p in PATTERNS)

def send_bot_message(text: str):
    """يرسل رسالة إلى القناة المستهدفة عبر البوت."""
    if not TARGET_CHANNEL_ID:
        print("خطأ فادح: لا يمكن الإرسال لأن TARGET_CHANNEL_ID غير معين.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TARGET_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",  # لتفعيل الروابط المنسقة
        "disable_web_page_preview": True
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if not resp.ok:
            print(f"فشل إرسال الإشعار: {resp.status_code} - {resp.text}")
    except requests.RequestException as e:
        print(f"خطأ في الشبكة أثناء إرسال الإشعار: {e}")

@client.on(events.NewMessage(incoming=True))
async def keyword_handler(event):
    """
    يعالج الرسائل الجديدة، ويتحقق من الشروط، ويرسل الإشعار.
    """
    # 1. تجاهل كل شيء ليس رسالة في مجموعة
    if not event.is_group:
        return

    text = event.raw_text or ""
    
    # 2. تحقق من وجود كلمة مفتاحية
    if not matches_any(text):
        return

    try:
        sender = await event.get_sender()
        chat = await event.get_chat()

        # قد لا يكون للمرسل أو المجموعة وجود (رسائل محذوفة، الخ)
        if not sender or not chat:
            return

        # 3. بناء الروابط والمعلومات
        # رابط مباشر للمستخدم (يعمل بالضغط عليه)
        user_link = f"[{sender.first_name or 'مستخدم'}](tg://user?id={sender.id})"

        # 4. تنسيق الرسالة النهائية
        message_to_send = (
            f"""
            🔔 **تم العثور على كلمة مفتاحية** 🔔

            📝 **نص الرسالة:**
            {text}

            👤 **المرسل:** {user_link}

            👥 **المجموعة:** {chat.title}"""
            )

        # 5. إرسال الإشعار
        send_bot_message(message_to_send)

    except Exception as e:
        print(f"حدث خطأ أثناء معالجة الرسالة {event.id}: {e}")
        # يمكنك تفعيل السطر التالي لإرسال أخطاء المعالجة إلى قناتك
        # send_bot_message(f"⚠️ حدث خطأ في المعالج: {e}")

async def main():
    """الدالة الرئيسية للتشغيل."""
    print("بدء جلسة تيليجرام (userbot)...")
    try:
        await client.start()
    except rpcerrorlist.ApiIdInvalidError:
        raise SystemExit("خطأ: تركيبة api_id/api_hash غير صحيحة.")
    except Exception as e:
        raise SystemExit(f"فشل في بدء الجلسة: {e}")

    me = await client.get_me()
    print(f"تم تسجيل الدخول بنجاح كـ: {me.first_name}")
    print("البوت الآن يراقب المجموعات بحثاً عن الكلمات المفتاحية...")
    
    if TARGET_CHANNEL_ID:
        send_bot_message("✅ **تم تفعيل المراقبة بنجاح**")

    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as e:
        if isinstance(e, SystemExit):
            print(str(e))
        else:
            print("تم إيقاف البوت.")
    except Exception as e:
        print(f"حدث خطأ غير متوقع أثناء التشغيل: {e}")

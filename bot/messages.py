# All texts use Telegram HTML parse mode; escape any user/AI text inserted here.

BOT_SHORT_DESCRIPTION = "ChatGPT, Claude, Gemini va boshqa AI'lar uchun aniq prompt yozib beraman."
BOT_DESCRIPTION = (
    "Prompter — oddiy g‘oyangizni boshqa AI uchun aniq, professional promptga aylantiradi.\n\n"
    "1) AI'ni tanlaysiz\n"
    "2) Vazifani yozasiz (rasm, fayl yoki namuna ham yuborishingiz mumkin)\n"
    "3) Tayyor promptni nusxalab, AI'ga yuborasiz\n\n"
    "Boshlash uchun «Start» tugmasini bosing."
)

WELCOME = (
    "👋 Salom, {name}! Men — <b>Prompter</b>.\n\n"
    "Men vazifani o‘zim bajarmayman. Men ChatGPT, Claude, Gemini kabi AI'lar uchun "
    "<b>aniq va kuchli prompt</b> yozib beraman — siz uni nusxalab, o‘sha AI'ga yuborasiz.\n\n"
    "<b>Qanday ishlaydi:</b>\n"
    "1️⃣ Prompt qaysi AI uchun ekanini tanlaysiz\n"
    "2️⃣ Vazifangizni yozasiz — kerak bo‘lsa, <b>avval</b> rasm, fayl yoki namuna yuborasiz\n"
    "3️⃣ Rejimni tanlaysiz va tayyor promptni olasiz\n\n"
    "Pastdagi menyu doim shu yerda turadi. Adashsangiz — ❓ Yordam."
)

HELP = (
    "<b>❓ Prompter qo‘llanmasi</b>\n\n"
    "<b>Bot nima qiladi?</b>\n"
    "Siz aytgan vazifadan boshqa AI uchun tayyor prompt yozadi. Vazifaning o‘zini bajarmaydi.\n\n"
    "<b>Qadamlar</b>\n"
    "1️⃣ <b>AI tanlash</b> — prompt qaysi AI uchun (ChatGPT, Claude…)\n"
    "2️⃣ <b>Vazifa</b> — nima kerakligini bitta xabarda yozing\n"
    "3️⃣ <b>Rejim</b>:\n"
    "   🤖 <i>AI o‘zi taxmin qilsin</i> — savolsiz, tez\n"
    "   🔍 <i>Aniqlashtirib tayyorlay</i> — 1–5 ta qisqa savol, natija aniqroq\n\n"
    "<b>📎 Materiallar (reference)</b>\n"
    "Vazifani yozishdan <b>oldin</b> yoki jarayon davomida shunchaki yuboring:\n"
    "• rasm / skrinshot / dizayn namunasi\n"
    "• PDF yoki matnli fayl (.txt, .md, .py, .json…)\n"
    "• forward qilingan xabar yoki «📝 Matnli namuna» tugmasi orqali matn\n"
    "Men ularni tahlil qilib, promptga qo‘shaman. Rasm izohi ham hisobga olinadi.\n\n"
    "<b>Tayyor promptdan keyin</b>\n"
    "🔄 Boshqa variant · 🎯 Boshqa AI uchun · ✨ Yangi prompt\n\n"
    "Barcha buyruqlar: /commands"
)

COMMANDS = (
    "<b>📋 Buyruqlar</b>\n\n"
    "/start — botni qaytadan boshlash\n"
    "/new — yangi prompt yaratish\n"
    "/materials — yuborilgan materiallarni ko‘rish va tozalash\n"
    "/reference — matnli namuna (reference) qo‘shish\n"
    "/cancel — joriy jarayonni bekor qilish\n"
    "/help — batafsil qo‘llanma\n"
    "/commands — shu ro‘yxat\n\n"
    "Buyruq yozish shart emas: pastdagi menyu tugmalari ham xuddi shu ishni qiladi."
)

CHOOSE_TARGET = "<b>1/3 qadam.</b> Prompt qaysi AI uchun tayyorlanadi? 👇"
TARGET_SELECTED = (
    "🎯 Tanlandi: <b>{target}</b>\n\n"
    "<b>2/3 qadam.</b> Vazifangizni bitta xabarda yozing.\n"
    "Masalan: <i>«Kofe do‘koni uchun Instagram'ga 5 ta post g‘oyasi»</i>\n\n"
    "📎 Rasm, skrinshot, PDF yoki fayl bo‘lsa — <b>avval shularni yuboring</b>, "
    "keyin vazifani yozing."
)
REQUEST_AGAIN = "✏️ Vazifani qaytadan yozing. Materiallar saqlanib qoldi ({count} ta)."
CHOOSE_MODE = (
    "<b>3/3 qadam.</b> Qanday tayyorlaymiz?\n\n"
    "🎯 AI: <b>{target}</b> · 📎 Materiallar: <b>{count}</b>\n\n"
    "🤖 <b>AI o‘zi taxmin qilsin</b> — savolsiz, darhol tayyor\n"
    "🔍 <b>Aniqlashtirib tayyorlay</b> — bir nechta qisqa savol, natija aniqroq"
)
PRESS_BUTTON = "Iltimos, yuqoridagi tugmalardan birini tanlang 👆"

ANALYZING = "⏳ So‘rovingizni tahlil qilyapman…"
PROCESSING = "⏳ Prompt tayyorlayapman…"
WAITING_FOR_MATERIALS = "⏳ Materiallar tahlili tugashini kutyapman…"
CLARIFICATION_PREFIX = "❔ <b>Savol {number}</b>\n\n"
CLARIFICATION_HINT = "\n\n<i>Javobingizni yozing yoki «⏭ Savollarsiz tayyorla» tugmasini bosing.</i>"

READY = (
    "✅ <b>Prompt tayyor!</b> ({target} uchun)\n"
    "Pastdagi blokni bosing — u nusxalanadi. Keyin {target}'ga yuboring."
)
READY_WITH_FILES = "💡 Maslahat: rasm/fayllarni ham prompt bilan birga {target}'ga yuborsangiz, natija yanada aniq bo‘ladi."
WHAT_NEXT = "Keyingi qadam? 👇"

REFERENCE_SAVED = "📎 Qabul qilindi: <b>{label}</b>\nJami materiallar: <b>{count}</b> ta."
REFERENCE_READING = "📎 Materialni o‘qiyapman…"
REFERENCE_NEXT_TARGET = "Endi prompt qaysi AI uchun ekanini tanlang 👇"
REFERENCE_NEXT_REQUEST = "Yana material yuborishingiz yoki endi vazifani yozishingiz mumkin ✍️"
REFERENCE_NEXT_MODE = "Material promptga qo‘shiladi. Endi rejimni tanlang 👇"
REFERENCE_NEXT_CLARIFY = "Material hisobga olinadi. Savolga javob berishda davom eting."
REFERENCE_CAPTION_HINT = "\n\nRasm izohi vazifaning o‘zi bo‘lsa — pastdagi tugmani bosing."
REFERENCE_TEXT_PROMPT = (
    "📝 Namuna matnni keyingi xabarda yuboring (masalan, uslub namunasi, talablar, eski prompt).\n"
    "U vazifa sifatida emas, <b>material</b> sifatida saqlanadi."
)
REFERENCE_LIMIT = "Materiallar soni chegarasiga yetdingiz ({limit} ta). Ortiqchalarini /materials orqali tozalang."
REFERENCE_TOO_BIG = "Fayl juda katta (10 MB dan oshmasin). Kichikroq fayl yuboring."
REFERENCE_UNSUPPORTED = (
    "Bu turdagi materialni hali o‘qiy olmayman.\n"
    "Qo‘llanadi: rasm, PDF, matnli fayllar (.txt, .md, .py, .json…) va matn."
)
REFERENCE_FAILED = "Materialni o‘qib bo‘lmadi. Iltimos, boshqa formatda yuboring yoki qayta urinib ko‘ring."

MATERIALS_EMPTY = (
    "📎 Hozircha material yo‘q.\n\n"
    "Rasm, PDF, fayl yoki forward qilingan xabarni shunchaki yuboring — "
    "men ularni keyingi promptda hisobga olaman."
)
MATERIALS_LIST = "📎 <b>Materiallar ({count} ta)</b>\n\n{items}\n\nUlar joriy promptda ishlatiladi."
MATERIALS_CLEARED = "🗑 Materiallar tozalandi."

TASKLESS = "Salom! 🙂 Qanday vazifa uchun prompt tayyorlaymiz? Uni bitta xabarda yozing."
TEXT_ONLY = "Iltimos, javobni matn ko‘rinishida yozing."
CANCELLED = "❌ Bekor qilindi. Yangi prompt uchun «✨ Yangi prompt» tugmasini bosing."
SESSION_EXPIRED = "Suhbat muddati tugagan. Iltimos, «✨ Yangi prompt» bilan qaytadan boshlang."
STALE_BUTTON = "Bu tugma eskirgan. «✨ Yangi prompt» tugmasini bosing."
UNEXPECTED = "⚠️ Kutilmagan xatolik yuz berdi. Iltimos, yana urinib ko‘ring."

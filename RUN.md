# Prompter Telegram Bot

Prompter oddiy foydalanuvchi so‘rovini bajarib bermaydi. U boshqa AI uchun aniq, copy qilishga qulay prompt tayyorlaydi.

## O‘rnatish

Python 3.11 yoki yangiroq ishlating.

```powershell
cd C:\Users\toshtem1rov_b\.codex\.chatgpt-projects\g-p-6a86b809207481919050db7159d03d9a\prompter-telegram
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` ichiga `GEMINI_API_KEY` va BotFather’dan olingan `TELEGRAM_BOT_TOKEN` ni yozing. Mavjud Gemini kalitingizni saqlab qolishingiz mumkin. `GEMINI_MODEL` ixtiyoriy.

## Ishga tushirish

```powershell
python main.py
```

Botda `/start` yuboring, avval final prompt qaysi AI uchun ekanini tanlang, keyin vazifani yozing va **ASSUME** yoki **CLARIFY** rejimini tugmalar bilan tanlang.
Yangi suhbat uchun `🔄 New prompt`, `🏠 Home`, `/new` yoki `/new_prompt`dan foydalaning. `/help` qisqa qo‘llanmani ochadi. `/reference` esa joriy promptga matnli reference qo‘shadi.

## Test

API kalitsiz, sun’iy AI javoblari bilan asosiy oqimlar tekshiriladi:

```powershell
python -m unittest discover -s tests -v
```

## Arxitektura

- `ai/GeminiEngine` — yagona faol provider; Groq oqimdan olib tashlangan.
- `architect/` — mavjud understander, decision engine, builder va reviewer logikasi.
- `bot/` — aiogram router, xabarlar, klaviaturalar hamda FSM holatlari.
- Target AI — final prompt manzili; u Gemini providerini almashtirmaydi.
- Reference — hozircha faqat matnli va faqat joriy prompt uchun vaqtinchalik kontekst.
- `MemoryStorage` — hozircha per-user FSM; keyinchalik storage adapter bilan persistent saqlash qo‘shilishi mumkin.

Bot loglarni `logging` orqali yuritadi. Production oqimida terminaldan `input()` yoki `print()` ishlatilmaydi.

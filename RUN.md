# Prompter Telegram Bot

Prompter oddiy foydalanuvchi so‘rovini bajarib bermaydi. U boshqa AI uchun aniq, copy qilishga qulay prompt tayyorlaydi.

## O‘rnatish

Python 3.11 yoki yangiroq ishlating.

```bash
cd prompter-bot
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # Windows: Copy-Item .env.example .env
```

`.env` ichiga `GEMINI_API_KEY` va BotFather’dan olingan `TELEGRAM_BOT_TOKEN` ni yozing.

### Gemini modellari

`GEMINI_MODELS` — vergul bilan ajratilgan modellar ro‘yxati, standart qiymat:
`gemini-3.5-flash-lite,gemini-2.5-flash-lite`. Birinchi model xato bersa (404, 429, 5xx
yoki bo‘sh javob), bot avtomatik keyingisiga o‘tadi. 404 bergan model qayta ishga
tushirilgunga qadar o‘tkazib yuboriladi. Eski `GEMINI_MODEL` o‘zgaruvchisi ham ishlaydi —
u faqat birinchi (asosiy) modelni belgilaydi.

## Ishga tushirish

```bash
python main.py
```

Botda `/start` yuboring, avval final prompt qaysi AI uchun ekanini tanlang, keyin vazifani yozing va **ASSUME** yoki **CLARIFY** rejimini tugmalar bilan tanlang.
Yangi suhbat uchun `🔄 New prompt`, `🏠 Home`, `/new` yoki `/new_prompt`dan foydalaning. `/help` qisqa qo‘llanmani ochadi. `/reference` esa joriy promptga matnli reference qo‘shadi.

## Test

API kalitsiz, sun’iy AI javoblari bilan asosiy oqimlar tekshiriladi:

```bash
python -m unittest discover -s tests -v
```

## Arxitektura

- `ai/GeminiEngine` — yagona faol provider; bir nechta Gemini modeli orasida avtomatik fallback qiladi.
- `architect/` — mavjud understander, decision engine, builder va reviewer logikasi.
- `bot/` — aiogram router, xabarlar, klaviaturalar hamda FSM holatlari.
- Target AI — final prompt manzili; u Gemini providerini almashtirmaydi.
- Reference — hozircha faqat matnli va faqat joriy prompt uchun vaqtinchalik kontekst.
- `MemoryStorage` — hozircha per-user FSM; keyinchalik storage adapter bilan persistent saqlash qo‘shilishi mumkin.

Bot loglarni `logging` orqali yuritadi. Production oqimida terminaldan `input()` yoki `print()` ishlatilmaydi.

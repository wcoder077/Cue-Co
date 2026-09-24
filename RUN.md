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
python bot.py
```

Botda `/start` yuboring. Bot 3 qadamda ishlaydi va har bir xabarda qaysi qadamda
ekaningiz ko‘rsatiladi:

1. **AI tanlash** — prompt qaysi AI uchun (ChatGPT, Claude…).
2. **Vazifa** — bitta xabarda yoziladi. Kerak bo‘lsa, **avval** materiallar yuboriladi.
3. **Rejim** — 🤖 taxmin qilsin yoki 🔍 aniqlashtirib (savollarni «⏭ Savollarsiz tayyorla» bilan o‘tkazib yuborish mumkin).

Tayyor promptdan keyin: 🔄 Boshqa variant, 🎯 Boshqa AI uchun, ✨ Yangi prompt.
Pastdagi doimiy menyu: ✨ Yangi prompt, 📎 Materiallar, ❓ Yordam, 📋 Buyruqlar.
Bot AI ishlayotgan paytda chatda «typing…» ko‘rsatadi.

### Materiallar (reference)

Alohida rejimga kirish shart emas — istalgan qadamda shunchaki yuboriladi:

- rasm/skrinshot va PDF — Gemini tahlil qilib, matnli tavsifga aylantiradi (izoh ham saqlanadi);
- matnli fayllar (.txt, .md, .py, .json…) — to‘g‘ridan-to‘g‘ri o‘qiladi;
- forward qilingan xabar — avtomatik material bo‘ladi;
- oddiy matnni material sifatida qo‘shish: «📝 Matnli namuna qo‘shish» tugmasi yoki `/reference`.

Rasm izohi vazifaning o‘zi bo‘lsa, «✅ Izohni vazifa sifatida ishlatish» tugmasi chiqadi.
Bitta promptga ko‘pi bilan 10 ta material, har bir fayl 10 MB gacha.

### Buyruqlar

`/start`, `/new`, `/materials`, `/reference`, `/cancel`, `/help`, `/commands`.
Bot ishga tushganda ular Telegram'dagi «/» menyusiga va bot tavsifiga avtomatik yoziladi.

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
- Reference — `bot/references.py`; rasm/PDF `PromptArchitect.analyze_reference` orqali matnga aylanadi, shuning uchun qolgan pipeline faqat matn bilan ishlaydi. Faqat joriy prompt uchun saqlanadi.
- `MemoryStorage` — hozircha per-user FSM; keyinchalik storage adapter bilan persistent saqlash qo‘shilishi mumkin.

Bot loglarni `logging` orqali yuritadi. Production oqimida terminaldan `input()` yoki `print()` ishlatilmaydi.

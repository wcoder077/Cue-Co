"""Taklif va shikoyatlar bo'limi.

Bir nechta bot uchun umumiy modul: murojaatlar bitta guruhga yuboriladi.
Guruhda bot xabariga reply qilinsa, javob murojaat egasiga yetkaziladi.

Ulash: dispatcher.include_router(feedback.router) — boshqa routerlardan OLDIN.
"""

import html
import logging
import os
import sqlite3
import time
from contextlib import closing, contextmanager, suppress
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReactionTypeEmoji,
    User,
)

logger = logging.getLogger(__name__)

# =========================
# SETTINGS
# =========================

FEEDBACK_CHAT_ID = int(os.getenv("FEEDBACK_CHAT_ID") or -1003283765837)
MIN_LENGTH = 10
MAX_LENGTH = 1000
COOLDOWN_SECONDS = 2 * 60
DAILY_LIMIT = 5
TIMEZONE = ZoneInfo("Asia/Tashkent")
DB_PATH = Path(__file__).with_name("feedback.db")

# kod: (emoji, nomi, hashtag)
KINDS = {
    "idea": ("💡", "Taklif", "taklif"),
    "complaint": ("⚠️", "Shikoyat", "shikoyat"),
    "bug": ("🐞", "Xatolik", "xatolik"),
}


class FeedbackState(StatesGroup):
    choosing_kind = State()
    writing = State()
    confirming = State()


router = Router(name="feedback")

# SkipHandler'dan keyin aiogram shu routerdagi keyingi handlerlarni ham tekshiradi,
# shuning uchun ular buyruqlarni ushlab qolmasligi kerak
NOT_COMMAND = ~F.text.startswith("/")


# =========================
# DATABASE
# =========================


@contextmanager
def _db():
    with closing(sqlite3.connect(DB_PATH)) as connection:
        with connection:
            yield connection


def _init_db():
    with _db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT,
                username TEXT,
                kind TEXT NOT NULL,
                text TEXT NOT NULL,
                group_message_id INTEGER,
                created_at REAL NOT NULL
            )
            """
        )


_init_db()


def _limit_error(user_id: int) -> str | None:
    now = time.time()
    with _db() as connection:
        last, today = connection.execute(
            "SELECT MAX(created_at), COUNT(*) FROM feedback "
            "WHERE user_id = ? AND created_at > ? AND group_message_id IS NOT NULL",
            (user_id, now - 24 * 3600),
        ).fetchone()

    if today >= DAILY_LIMIT:
        return (
            f"⛔ Bir kunda {DAILY_LIMIT} tadan ortiq murojaat yuborib bo'lmaydi.\n"
            "Ertaga qayta urinib ko'ring."
        )
    if last and now - last < COOLDOWN_SECONDS:
        wait = int(COOLDOWN_SECONDS - (now - last)) + 1
        return f"⏳ Keyingi murojaatni {wait} soniyadan keyin yuborishingiz mumkin."
    return None


def _save(user: User, kind: str, text: str) -> int:
    with _db() as connection:
        return connection.execute(
            "INSERT INTO feedback (user_id, full_name, username, kind, text, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user.id, user.full_name, user.username, kind, text, time.time()),
        ).lastrowid


def _set_group_message(feedback_id: int, message_id: int | None):
    with _db() as connection:
        if message_id is None:
            connection.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
        else:
            connection.execute(
                "UPDATE feedback SET group_message_id = ? WHERE id = ?",
                (message_id, feedback_id),
            )


def _find_by_group_message(message_id: int):
    with _db() as connection:
        return connection.execute(
            "SELECT id, user_id, kind, text FROM feedback WHERE group_message_id = ?",
            (message_id,),
        ).fetchone()


# =========================
# TEXTS AND KEYBOARDS
# =========================

CANCEL_BUTTON = InlineKeyboardButton(text="❌ Bekor qilish", callback_data="fb:cancel")


def _kind_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{emoji} {title}", callback_data=f"fb:kind:{code}")
                for code, (emoji, title, _) in KINDS.items()
            ],
            [CANCEL_BUTTON],
        ]
    )


def _writing_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="fb:back"), CANCEL_BUTTON]
        ]
    )


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Yuborish", callback_data="fb:send")],
            [
                InlineKeyboardButton(text="✏️ Qayta yozish", callback_data="fb:edit"),
                CANCEL_BUTTON,
            ],
        ]
    )


INTRO_TEXT = (
    "📝 <b>Taklif va shikoyatlar</b>\n\n"
    "Fikringiz biz uchun muhim! Har bir murojaat dasturchiga yetkaziladi "
    "va javob shu chatga keladi.\n\n"
    "Murojaat turini tanlang 👇"
)


def _writing_text(kind: str) -> str:
    emoji, title, _ = KINDS[kind]
    return (
        f"{emoji} <b>{title}</b>\n\n"
        "Fikringizni <b>bitta xabarda</b> yozib yuboring ✍️\n\n"
        f"📏 Uzunligi: {MIN_LENGTH}–{MAX_LENGTH} belgi\n"
        f"📅 Kuniga ko'pi bilan {DAILY_LIMIT} ta murojaat"
    )


def _preview_text(kind: str, text: str) -> str:
    emoji, title, _ = KINDS[kind]
    return (
        "👀 <b>Murojaatingizni tekshiring</b>\n\n"
        f"{emoji} <b>{title}</b> · {len(text)} belgi\n"
        f"<blockquote>{html.escape(text)}</blockquote>\n\n"
        "Hammasi to'g'rimi?"
    )


def _group_text(feedback_id: int, kind: str, user: User, bot_user: User, text: str) -> str:
    emoji, title, tag = KINDS[kind]
    username = f"@{html.escape(user.username)}" if user.username else "yo'q"
    sent_at = datetime.now(TIMEZONE).strftime("%d.%m.%Y · %H:%M")
    return (
        f"{emoji} <b>{title.upper()} №{feedback_id}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>Bot:</b> {html.escape(bot_user.full_name)} (@{bot_user.username})\n"
        f"👤 <b>Ism:</b> <a href=\"tg://user?id={user.id}\">{html.escape(user.full_name)}</a>\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"🕒 <b>Vaqt:</b> {sent_at}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote expandable>{html.escape(text)}</blockquote>\n\n"
        f"#{tag} #{bot_user.username}\n"
        "<i>↩️ Javob berish uchun shu xabarga reply qiling</i>"
    )


async def _edit(message: Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except TelegramAPIError:
        await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")


# =========================
# GROUP: ANSWERS TO USERS
# =========================


@router.message(F.chat.id == FEEDBACK_CHAT_ID)
async def group_message(message: Message, bot: Bot):
    """Guruhda bot murojaatiga reply qilinsa — javobni foydalanuvchiga yuboradi."""
    reply_to = message.reply_to_message
    answer = message.text or message.caption
    if not reply_to or not reply_to.from_user or reply_to.from_user.id != bot.id or not answer:
        return

    row = _find_by_group_message(reply_to.message_id)
    if not row:
        return

    feedback_id, user_id, kind, original = row
    emoji, title, _ = KINDS.get(kind, KINDS["idea"])
    short = original if len(original) <= 300 else original[:300] + "…"

    try:
        await bot.send_message(
            user_id,
            f"📬 <b>Murojaatingizga javob keldi</b>\n\n"
            f"{emoji} <b>{title} №{feedback_id}:</b>\n"
            f"<blockquote>{html.escape(short)}</blockquote>\n\n"
            f"💬 {html.escape(answer)}",
            parse_mode="HTML",
        )
    except TelegramAPIError as e:
        await message.reply(f"❌ Javob yetkazilmadi: {html.escape(str(e))}", parse_mode="HTML")
        return

    with suppress(TelegramAPIError):
        await message.react([ReactionTypeEmoji(emoji="👍")])


# =========================
# USER FLOW
# =========================


@router.message(Command("taklif"), F.chat.type == "private")
async def feedback_start(message: Message, state: FSMContext):
    await state.clear()
    if error := _limit_error(message.from_user.id):
        await message.answer(error)
        return
    await state.set_state(FeedbackState.choosing_kind)
    await message.answer(INTRO_TEXT, reply_markup=_kind_keyboard(), parse_mode="HTML")


@router.message(Command("cancel"), StateFilter(FeedbackState))
async def feedback_cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❎ Murojaat bekor qilindi.")


@router.message(StateFilter(FeedbackState), F.text.startswith("/"))
async def feedback_other_command(message: Message, state: FSMContext):
    # Boshqa buyruq yuborilsa — murojaatni tashlab, buyruqni botning o'ziga o'tkazamiz
    await state.clear()
    raise SkipHandler()


@router.message(StateFilter(FeedbackState.writing, FeedbackState.confirming), F.text, NOT_COMMAND)
async def feedback_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if len(text) < MIN_LENGTH:
        await message.answer(
            f"✏️ Murojaat juda qisqa ({len(text)} belgi). "
            f"Kamida {MIN_LENGTH} belgi yozing."
        )
        return
    if len(text) > MAX_LENGTH:
        await message.answer(
            f"✂️ Murojaat juda uzun ({len(text)} belgi). "
            f"Ko'pi bilan {MAX_LENGTH} belgi bo'lishi kerak — qisqartirib qayta yuboring."
        )
        return

    data = await state.get_data()
    await state.update_data(text=text)
    await state.set_state(FeedbackState.confirming)
    await message.answer(
        _preview_text(data.get("kind", "idea"), text),
        reply_markup=_confirm_keyboard(),
        parse_mode="HTML",
    )


@router.message(FeedbackState.writing, NOT_COMMAND)
async def feedback_not_text(message: Message):
    await message.answer("✍️ Iltimos, murojaatni matn ko'rinishida yozing.")


@router.message(StateFilter(FeedbackState.choosing_kind, FeedbackState.confirming), NOT_COMMAND)
async def feedback_use_buttons(message: Message):
    await message.answer("👆 Iltimos, yuqoridagi tugmalardan birini tanlang.")


@router.callback_query(F.data.startswith("fb:kind:"), FeedbackState.choosing_kind)
async def feedback_kind(callback: CallbackQuery, state: FSMContext):
    kind = callback.data.removeprefix("fb:kind:")
    if kind not in KINDS:
        await callback.answer()
        return
    await state.update_data(kind=kind)
    await state.set_state(FeedbackState.writing)
    await _edit(callback.message, _writing_text(kind), _writing_keyboard())
    await callback.answer()


@router.callback_query(F.data == "fb:back", StateFilter(FeedbackState))
async def feedback_back(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FeedbackState.choosing_kind)
    await _edit(callback.message, INTRO_TEXT, _kind_keyboard())
    await callback.answer()


@router.callback_query(F.data == "fb:edit", FeedbackState.confirming)
async def feedback_edit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(FeedbackState.writing)
    await _edit(callback.message, _writing_text(data.get("kind", "idea")), _writing_keyboard())
    await callback.answer()


@router.callback_query(F.data == "fb:cancel")
async def feedback_cancel(callback: CallbackQuery, state: FSMContext):
    if await state.get_state() in FeedbackState.__state_names__:
        await state.clear()
    await _edit(callback.message, "❎ Murojaat bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data == "fb:send", FeedbackState.confirming)
async def feedback_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user = callback.from_user
    if error := _limit_error(user.id):
        await state.clear()
        await _edit(callback.message, error)
        await callback.answer()
        return

    data = await state.get_data()
    kind, text = data.get("kind", "idea"), data.get("text")
    if not text:
        await state.clear()
        await callback.answer("Murojaat eskirgan, /taklif ni qaytadan bosing.", show_alert=True)
        return

    feedback_id = _save(user, kind, text)
    try:
        sent = await bot.send_message(
            FEEDBACK_CHAT_ID,
            _group_text(feedback_id, kind, user, await bot.me(), text),
            parse_mode="HTML",
        )
    except TelegramAPIError:
        logger.exception("Murojaat guruhga yuborilmadi")
        _set_group_message(feedback_id, None)
        await callback.answer(
            "❌ Hozir yuborib bo'lmadi. Birozdan keyin qayta urinib ko'ring.",
            show_alert=True,
        )
        return

    _set_group_message(feedback_id, sent.message_id)
    await state.clear()
    emoji, title, _ = KINDS[kind]
    await _edit(
        callback.message,
        f"✅ <b>Murojaatingiz yuborildi!</b>\n\n"
        f"{emoji} {title} №{feedback_id}\n"
        f"<blockquote>{html.escape(text)}</blockquote>\n\n"
        "Rahmat! Dasturchi javob bersa, u shu chatga keladi 🤝",
    )
    await callback.answer("Yuborildi ✅")

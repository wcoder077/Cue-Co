from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# Reply-menu texts are matched in handlers, so they live in one place.
MENU_NEW = "✨ Yangi prompt"
MENU_MATERIALS = "📎 Materiallar"
MENU_HELP = "❓ Yordam"
MENU_COMMANDS = "📋 Buyruqlar"

TARGETS = {
    "chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini",
    "deepseek": "DeepSeek", "copilot": "Microsoft Copilot",
    "perplexity": "Perplexity", "notebooklm": "NotebookLM", "other": "Boshqa AI",
}


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_NEW), KeyboardButton(text=MENU_MATERIALS)],
            [KeyboardButton(text=MENU_HELP), KeyboardButton(text=MENU_COMMANDS)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Vazifa yozing yoki material yuboring…",
    )


def target_ai_keyboard(prefix: str = "target") -> InlineKeyboardMarkup:
    buttons = [_button(name, f"{prefix}:{key}") for key, name in TARGETS.items()]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)])


def request_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_button("📝 Matnli namuna qo‘shish", "add_text_reference")],
        [_button("🎯 AI'ni o‘zgartirish", "change_target"), _button("❌ Bekor qilish", "cancel")],
    ])


def caption_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_button("✅ Izohni vazifa sifatida ishlatish", "caption_as_task")],
    ])


def reference_input_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_button("⬅️ Ortga", "reference_back")]])


def materials_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_button("🗑 Hammasini tozalash", "clear_materials")]])


def mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_button("🤖 AI o‘zi taxmin qilsin", "mode:ASSUME")],
        [_button("🔍 Aniqlashtirib tayyorlay", "mode:CLARIFY")],
        [_button("✏️ Vazifani o‘zgartirish", "edit_request"), _button("❌ Bekor qilish", "cancel")],
    ])


def clarify_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_button("⏭ Savollarsiz tayyorla", "finish_now")]])


def final_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_button("🔄 Boshqa variant", "regenerate"), _button("🎯 Boshqa AI uchun", "retarget")],
        [_button("✨ Yangi prompt", "new_prompt")],
    ])


def new_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_button("✨ Yangi prompt", "new_prompt")]])

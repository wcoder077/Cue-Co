from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 AI o‘zi taxmin qilsin", callback_data="mode:ASSUME")],
        [InlineKeyboardButton(text="🔍 Aniqlashtirib tayyorlay", callback_data="mode:CLARIFY")],
    ])


def target_ai_keyboard() -> InlineKeyboardMarkup:
    targets = [
        ("ChatGPT", "chatgpt"), ("Claude", "claude"),
        ("Gemini", "gemini"), ("DeepSeek", "deepseek"),
        ("Microsoft Copilot", "copilot"), ("Perplexity", "perplexity"),
        ("NotebookLM", "notebooklm"), ("Boshqa AI", "other"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"target:{value}")]
        for name, value in targets
    ])


def new_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Copy prompt", callback_data="copy_prompt")],
        [InlineKeyboardButton(text="🔄 New prompt", callback_data="new_prompt")],
        [InlineKeyboardButton(text="🏠 Home", callback_data="home")],
    ])

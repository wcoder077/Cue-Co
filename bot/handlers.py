import asyncio
import html
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from architect import PromptArchitect
from architect.state import ConversationState

from . import messages
from .keyboards import mode_keyboard, new_prompt_keyboard, target_ai_keyboard
from .states import PromptStates
from .task_detection import is_taskless

logger = logging.getLogger(__name__)
router = Router()

TARGETS = {
    "chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini",
    "deepseek": "DeepSeek", "copilot": "Microsoft Copilot",
    "perplexity": "Perplexity", "notebooklm": "NotebookLM", "other": "Boshqa AI",
}


async def _save_conversation(state: FSMContext, conversation: ConversationState) -> None:
    await state.update_data(conversation=conversation.to_dict())


async def _load_conversation(state: FSMContext) -> ConversationState:
    data = await state.get_data()
    return ConversationState.from_dict(data["conversation"])


async def _show_target_selection(message: Message, state: FSMContext, welcome: bool = False) -> None:
    await state.clear()
    await state.set_state(PromptStates.waiting_for_target)
    if welcome:
        await message.answer(messages.WELCOME)
    await message.answer(messages.CHOOSE_TARGET, reply_markup=target_ai_keyboard())


async def _send_final(message: Message, prompt: str) -> None:
    await message.answer(messages.READY)
    # Telegram messages max at 4096 chars. Keep each escaped code block safe.
    for start in range(0, len(prompt), 3600):
        chunk = html.escape(prompt[start:start + 3600])
        await message.answer(f"<pre><code>{chunk}</code></pre>")
    await message.answer("", reply_markup=new_prompt_keyboard())


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await _show_target_selection(message, state, welcome=True)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(messages.HELP)


@router.message(Command("reference"))
async def reference_command(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        current_state = PromptStates.waiting_for_target.state
    await state.update_data(reference_return_state=current_state)
    await state.set_state(PromptStates.waiting_for_reference)
    await message.answer(messages.REFERENCE_PROMPT)


@router.message(Command("new", "new_prompt"))
async def new_prompt_command(message: Message, state: FSMContext) -> None:
    await _show_target_selection(message, state)


@router.callback_query(F.data.in_({"new_prompt", "home"}))
async def reset_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _show_target_selection(callback.message, state)


@router.callback_query(F.data == "copy_prompt")
async def copy_prompt(callback: CallbackQuery) -> None:
    # Telegram clients, not bots, own clipboard access. Keep this honest.
    await callback.answer("Prompt code block ichidagi Copy tugmasi orqali nusxalanadi.", show_alert=True)


@router.callback_query(PromptStates.waiting_for_target, F.data.startswith("target:"))
async def choose_target(callback: CallbackQuery, state: FSMContext) -> None:
    target_key = callback.data.split(":", 1)[1]
    target = TARGETS.get(target_key)
    if target is None:
        await callback.answer("Bu AI tanlovi topilmadi.", show_alert=True)
        return
    await state.update_data(target_ai=target, references=[])
    await state.set_state(PromptStates.waiting_for_request)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(messages.TARGET_SELECTED.format(target=target))


@router.message(PromptStates.waiting_for_reference, F.text)
async def receive_reference(message: Message, state: FSMContext) -> None:
    reference = message.text.strip()
    if not reference:
        await message.answer(messages.TEXT_ONLY)
        return
    data = await state.get_data()
    references = data.get("references", [])
    references.append(reference)
    await state.update_data(references=references)
    if conversation_data := data.get("conversation"):
        conversation = ConversationState.from_dict(conversation_data)
        conversation.add_reference(reference)
        await _save_conversation(state, conversation)
    return_state = data.get("reference_return_state", PromptStates.waiting_for_request.state)
    await state.set_state(return_state)
    await message.answer(messages.REFERENCE_SAVED)


@router.message(PromptStates.waiting_for_reference)
async def unsupported_reference(message: Message) -> None:
    await message.answer(messages.REFERENCE_UNSUPPORTED)


@router.message(PromptStates.waiting_for_request, F.text)
async def receive_request(message: Message, state: FSMContext, architect: PromptArchitect) -> None:
    text = message.text.strip()
    if is_taskless(text):
        await message.answer(messages.TASKLESS)
        return
    try:
        data = await state.get_data()
        conversation, _ = await asyncio.to_thread(
            architect.begin, text, data.get("target_ai", ""), data.get("references", []),
        )
        await _save_conversation(state, conversation)
        await state.set_state(PromptStates.waiting_for_mode)
        await message.answer(messages.CHOOSE_MODE, reply_markup=mode_keyboard())
    except Exception:
        logger.exception("Could not understand request for user %s", message.from_user.id)
        await message.answer(messages.UNEXPECTED)


@router.message(PromptStates.waiting_for_request)
async def request_must_be_text(message: Message) -> None:
    await message.answer(messages.TEXT_ONLY)


@router.message(PromptStates.waiting_for_mode)
async def mode_must_be_button(message: Message) -> None:
    await message.answer("Iltimos, yuqoridagi tugmalardan birini tanlang.", reply_markup=mode_keyboard())


@router.callback_query(PromptStates.waiting_for_mode, F.data.in_({"mode:ASSUME", "mode:CLARIFY"}))
async def choose_mode(callback: CallbackQuery, state: FSMContext, architect: PromptArchitect) -> None:
    mode = callback.data.split(":", 1)[1]
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(messages.PROCESSING)
    try:
        conversation = await _load_conversation(state)
        result = await asyncio.to_thread(architect.choose_mode, conversation, mode)
        await _save_conversation(state, conversation)
        if result["status"] == "NEED_CLARIFICATION":
            await state.set_state(PromptStates.clarifying)
            await callback.message.answer(messages.CLARIFICATION_PREFIX + result["questions"][0])
        else:
            await state.set_state(PromptStates.completed)
            await _send_final(callback.message, result["prompt"])
    except (KeyError, ValueError):
        await state.set_state(PromptStates.waiting_for_request)
        await callback.message.answer("Suhbat muddati tugagan. Iltimos, vazifani yana yuboring.")
    except Exception:
        logger.exception("Could not apply mode for user %s", callback.from_user.id)
        await callback.message.answer(messages.UNEXPECTED)


@router.message(PromptStates.clarifying, F.text)
async def receive_answer(message: Message, state: FSMContext, architect: PromptArchitect) -> None:
    try:
        conversation = await _load_conversation(state)
        result = await asyncio.to_thread(architect.answer, conversation, message.text)
        await _save_conversation(state, conversation)
        if result["status"] == "NEED_CLARIFICATION":
            await message.answer(messages.CLARIFICATION_PREFIX + result["questions"][0])
        else:
            await state.set_state(PromptStates.completed)
            await _send_final(message, result["prompt"])
    except (KeyError, ValueError):
        await state.set_state(PromptStates.waiting_for_request)
        await message.answer("Suhbat muddati tugagan. Iltimos, vazifani yana yuboring.")
    except Exception:
        logger.exception("Could not process clarification answer for user %s", message.from_user.id)
        await message.answer(messages.UNEXPECTED)


@router.message(PromptStates.clarifying)
async def clarification_must_be_text(message: Message) -> None:
    await message.answer(messages.TEXT_ONLY)


@router.message(PromptStates.completed, F.text)
async def completed_message(message: Message) -> None:
    await message.answer("Yangi prompt uchun 🔄 New prompt tugmasini bosing.", reply_markup=new_prompt_keyboard())

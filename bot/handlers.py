import asyncio
import html
import logging
from collections import defaultdict
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.chat_action import ChatActionSender

from architect import PromptArchitect
from architect.state import ConversationState

from . import messages
from .keyboards import (
    MENU_COMMANDS, MENU_HELP, MENU_MATERIALS, MENU_NEW, TARGETS,
    caption_keyboard, clarify_keyboard, final_keyboard, main_menu, materials_keyboard,
    mode_keyboard, new_prompt_keyboard, reference_input_keyboard, request_keyboard,
    target_ai_keyboard,
)
from .references import (
    MAX_FILE_BYTES, MAX_REFERENCES, decode_text, document_kind, format_reference, reference_label,
)
from .states import PromptStates
from .task_detection import is_taskless

logger = logging.getLogger(__name__)
router = Router()

# aiogram handles updates concurrently (e.g. an album arrives as several updates),
# so reference read-modify-write goes through a per-user lock.
_locks: defaultdict[tuple, asyncio.Lock] = defaultdict(asyncio.Lock)
# Attachments still being analysed; a request waits for them so nothing is missed.
_pending: defaultdict[tuple, int] = defaultdict(int)
# One acknowledgement per album instead of one per photo.
_album_acks: dict[str, Message] = {}
_ack_locks: defaultdict[tuple, asyncio.Lock] = defaultdict(asyncio.Lock)

FILE_LABELS = ("Rasm", "PDF", "Fayl")


def _key(state: FSMContext) -> tuple:
    return state.key.chat_id, state.key.user_id


def _typing(message: Message) -> ChatActionSender:
    """Shows "typing…" in the chat, repeated every 5s, while the block runs."""
    return ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id)


async def _delete(message: Message | None) -> None:
    if message is not None:
        with suppress(TelegramBadRequest):
            await message.delete()


async def _save_conversation(state: FSMContext, conversation: ConversationState) -> None:
    await state.update_data(conversation=conversation.to_dict())


async def _load_conversation(state: FSMContext) -> ConversationState:
    data = await state.get_data()
    return ConversationState.from_dict(data["conversation"])


async def _get_references(state: FSMContext) -> list[str]:
    data = await state.get_data()
    if conversation := data.get("conversation"):
        return conversation.get("references", [])
    return data.get("references", [])


async def _add_reference(state: FSMContext, reference: str) -> int | None:
    """Store a reference for the current prompt; returns the new count or None if full."""
    async with _locks[_key(state)]:
        data = await state.get_data()
        if conversation_data := data.get("conversation"):
            conversation = ConversationState.from_dict(conversation_data)
            if len(conversation.references) >= MAX_REFERENCES:
                return None
            conversation.add_reference(reference)
            await _save_conversation(state, conversation)
            return len(conversation.references)
        references = data.get("references", [])
        if len(references) >= MAX_REFERENCES:
            return None
        references.append(reference)
        await state.update_data(references=references)
        return len(references)


async def _clear_references(state: FSMContext) -> None:
    async with _locks[_key(state)]:
        data = await state.get_data()
        if conversation_data := data.get("conversation"):
            conversation = ConversationState.from_dict(conversation_data)
            conversation.references = []
            await _save_conversation(state, conversation)
        await state.update_data(references=[])


async def _wait_for_references(message: Message, state: FSMContext) -> None:
    key = _key(state)
    if not _pending[key]:
        return
    notice = await message.answer(messages.WAITING_FOR_MATERIALS)
    async with _typing(message):
        for _ in range(120):  # at most ~60s
            if not _pending[key]:
                break
            await asyncio.sleep(0.5)
    await _delete(notice)


async def _show_target_selection(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(PromptStates.waiting_for_target)
    await message.answer(messages.CHOOSE_TARGET, reply_markup=target_ai_keyboard())


async def _ask_for_request(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(PromptStates.waiting_for_request)
    await message.answer(
        messages.TARGET_SELECTED.format(target=html.escape(data.get("target_ai", ""))),
        reply_markup=request_keyboard(),
    )


def _split_escaped(text: str, limit: int = 4000) -> list[str]:
    """Split text so every HTML-escaped chunk fits Telegram's 4096-char limit."""
    chunks, current, size = [], [], 0
    for line in text.splitlines(keepends=True):
        for piece in (line[i:i + 500] for i in range(0, len(line), 500)):
            escaped = html.escape(piece)
            if current and size + len(escaped) > limit:
                chunks.append("".join(current))
                current, size = [], 0
            current.append(escaped)
            size += len(escaped)
    if current:
        chunks.append("".join(current))
    return chunks


async def _send_final(message: Message, conversation: ConversationState, prompt: str) -> None:
    target = html.escape(conversation.target_ai or "AI")
    await message.answer(messages.READY.format(target=target))
    for chunk in _split_escaped(prompt.strip()):
        await message.answer(f"<pre><code>{chunk}</code></pre>")
    if any(reference_label(r).startswith(FILE_LABELS) for r in conversation.references):
        await message.answer(messages.READY_WITH_FILES.format(target=target))
    await message.answer(messages.WHAT_NEXT, reply_markup=final_keyboard())


async def _send_question(message: Message, conversation: ConversationState, question: str) -> None:
    # AI text may contain <, > or &; the bot uses HTML parse mode.
    await message.answer(
        messages.CLARIFICATION_PREFIX.format(number=len(conversation.qa_history) + 1)
        + html.escape(question) + messages.CLARIFICATION_HINT,
        reply_markup=clarify_keyboard(),
    )


async def _run_step(message: Message, state: FSMContext, step, status_text: str = messages.PROCESSING) -> None:
    """Run a blocking architect step with a status message and "typing…" indicator."""
    await _wait_for_references(message, state)
    status = await message.answer(status_text)
    try:
        conversation = await _load_conversation(state)
        async with _typing(message):
            result = await asyncio.to_thread(step, conversation)
        await _save_conversation(state, conversation)
    except KeyError:
        await state.clear()
        await message.answer(messages.SESSION_EXPIRED, reply_markup=new_prompt_keyboard())
        return
    finally:
        await _delete(status)
    if result["status"] == "NEED_CLARIFICATION":
        await state.set_state(PromptStates.clarifying)
        await _send_question(message, conversation, result["questions"][0])
    else:
        await state.set_state(PromptStates.completed)
        await _send_final(message, conversation, result["prompt"])


async def _start_request(message: Message, state: FSMContext, architect: PromptArchitect, text: str) -> None:
    if is_taskless(text):
        await message.answer(messages.TASKLESS)
        return
    await _wait_for_references(message, state)
    status = await message.answer(messages.ANALYZING)
    try:
        data = await state.get_data()
        async with _typing(message):
            conversation, _ = await asyncio.to_thread(
                architect.begin, text, data.get("target_ai", ""), data.get("references", []),
            )
    except Exception:
        logger.exception("Could not understand request in chat %s", message.chat.id)
        await message.answer(messages.UNEXPECTED)
        return
    finally:
        await _delete(status)
    await _save_conversation(state, conversation)
    await state.update_data(pending_task=None)
    await state.set_state(PromptStates.waiting_for_mode)
    await message.answer(
        messages.CHOOSE_MODE.format(
            target=html.escape(conversation.target_ai), count=len(conversation.references),
        ),
        reply_markup=mode_keyboard(),
    )


# --- Commands and the persistent reply menu (registered first so they win in every state) ---

@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    name = html.escape(message.from_user.first_name or "do‘stim")
    await message.answer(messages.WELCOME.format(name=name), reply_markup=main_menu())
    await _show_target_selection(message, state)


@router.message(Command("help"))
@router.message(F.text == MENU_HELP)
async def help_command(message: Message) -> None:
    await message.answer(messages.HELP, reply_markup=main_menu())


@router.message(Command("commands"))
@router.message(F.text == MENU_COMMANDS)
async def commands_command(message: Message) -> None:
    await message.answer(messages.COMMANDS, reply_markup=main_menu())


@router.message(Command("new", "new_prompt"))
@router.message(F.text == MENU_NEW)
async def new_prompt_command(message: Message, state: FSMContext) -> None:
    await _show_target_selection(message, state)


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(messages.CANCELLED, reply_markup=main_menu())


@router.message(Command("materials", "references"))
@router.message(F.text == MENU_MATERIALS)
async def materials_command(message: Message, state: FSMContext) -> None:
    references = await _get_references(state)
    if not references:
        await message.answer(messages.MATERIALS_EMPTY)
        return
    items = "\n".join(f"{i}. {html.escape(reference_label(r))}" for i, r in enumerate(references, 1))
    await message.answer(
        messages.MATERIALS_LIST.format(count=len(references), items=items),
        reply_markup=materials_keyboard(),
    )


@router.message(Command("reference"))
async def reference_command(message: Message, state: FSMContext) -> None:
    await _enter_text_reference(message, state)


async def _enter_text_reference(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state in (None, PromptStates.completed.state):
        await _show_target_selection(message, state)
        current_state = PromptStates.waiting_for_target.state
    if current_state != PromptStates.waiting_for_reference.state:
        await state.update_data(reference_return_state=current_state)
    await state.set_state(PromptStates.waiting_for_reference)
    await message.answer(messages.REFERENCE_TEXT_PROMPT, reply_markup=reference_input_keyboard())


# --- Inline buttons ---

@router.callback_query(F.data.in_({"new_prompt", "home"}))
async def reset_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _show_target_selection(callback.message, state)


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(messages.CANCELLED, reply_markup=new_prompt_keyboard())


@router.callback_query(F.data == "clear_materials")
async def clear_materials(callback: CallbackQuery, state: FSMContext) -> None:
    await _clear_references(state)
    await callback.answer(messages.MATERIALS_CLEARED)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(messages.MATERIALS_CLEARED)


@router.callback_query(F.data == "add_text_reference")
async def add_text_reference(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _enter_text_reference(callback.message, state)


@router.callback_query(PromptStates.waiting_for_reference, F.data == "reference_back")
async def reference_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    await _return_from_reference(callback.message, state)


async def _return_from_reference(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    return_state = data.get("reference_return_state") or PromptStates.waiting_for_request.state
    await state.set_state(return_state)
    # Re-show the buttons the user still needs to press.
    if return_state == PromptStates.waiting_for_target.state:
        await message.answer(messages.CHOOSE_TARGET, reply_markup=target_ai_keyboard())
    elif return_state == PromptStates.waiting_for_mode.state:
        await message.answer(messages.PRESS_BUTTON, reply_markup=mode_keyboard())
    elif return_state == PromptStates.waiting_for_request.state:
        await message.answer(messages.REFERENCE_NEXT_REQUEST, reply_markup=request_keyboard())


@router.callback_query(PromptStates.waiting_for_target, F.data.startswith("target:"))
async def choose_target(callback: CallbackQuery, state: FSMContext) -> None:
    target = TARGETS.get(callback.data.split(":", 1)[1])
    if target is None:
        await callback.answer("Bu AI tanlovi topilmadi.", show_alert=True)
        return
    # References sent before choosing a target are kept.
    await state.update_data(target_ai=target)
    await callback.answer()
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    await _ask_for_request(callback.message, state)


@router.callback_query(PromptStates.waiting_for_request, F.data == "change_target")
async def change_target(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(PromptStates.waiting_for_target)
    await callback.message.answer(messages.CHOOSE_TARGET, reply_markup=target_ai_keyboard())


@router.callback_query(PromptStates.waiting_for_request, F.data == "caption_as_task")
async def caption_as_task(callback: CallbackQuery, state: FSMContext, architect: PromptArchitect) -> None:
    data = await state.get_data()
    task = data.get("pending_task")
    if not task:
        await callback.answer(messages.STALE_BUTTON, show_alert=True)
        return
    await callback.answer()
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    await _start_request(callback.message, state, architect, task)


@router.callback_query(PromptStates.waiting_for_mode, F.data == "edit_request")
async def edit_request(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    references = (data.get("conversation") or {}).get("references", data.get("references", []))
    await state.update_data(conversation=None, references=references)
    await state.set_state(PromptStates.waiting_for_request)
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        messages.REQUEST_AGAIN.format(count=len(references)), reply_markup=request_keyboard(),
    )


@router.callback_query(PromptStates.waiting_for_mode, F.data.in_({"mode:ASSUME", "mode:CLARIFY"}))
async def choose_mode(callback: CallbackQuery, state: FSMContext, architect: PromptArchitect) -> None:
    mode = callback.data.split(":", 1)[1]
    await callback.answer()
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    try:
        await _run_step(callback.message, state, lambda c: architect.choose_mode(c, mode))
    except Exception:
        logger.exception("Could not apply mode in chat %s", callback.message.chat.id)
        # State is unchanged, so the user can simply press the button again.
        await callback.message.answer(messages.UNEXPECTED, reply_markup=mode_keyboard())


@router.callback_query(PromptStates.clarifying, F.data == "finish_now")
async def finish_now(callback: CallbackQuery, state: FSMContext, architect: PromptArchitect) -> None:
    await callback.answer()
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    try:
        await _run_step(callback.message, state, architect.finish)
    except Exception:
        logger.exception("Could not finish prompt in chat %s", callback.message.chat.id)
        await callback.message.answer(messages.UNEXPECTED, reply_markup=clarify_keyboard())


@router.callback_query(PromptStates.completed, F.data == "regenerate")
async def regenerate(callback: CallbackQuery, state: FSMContext, architect: PromptArchitect) -> None:
    await callback.answer()
    try:
        await _run_step(callback.message, state, architect.finish)
    except Exception:
        logger.exception("Could not regenerate prompt in chat %s", callback.message.chat.id)
        await callback.message.answer(messages.UNEXPECTED, reply_markup=final_keyboard())


@router.callback_query(PromptStates.completed, F.data == "retarget")
async def retarget_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(messages.CHOOSE_TARGET, reply_markup=target_ai_keyboard("retarget"))


@router.callback_query(PromptStates.completed, F.data.startswith("retarget:"))
async def retarget(callback: CallbackQuery, state: FSMContext, architect: PromptArchitect) -> None:
    target = TARGETS.get(callback.data.split(":", 1)[1])
    if target is None:
        await callback.answer("Bu AI tanlovi topilmadi.", show_alert=True)
        return
    await callback.answer()
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)

    def rebuild(conversation: ConversationState) -> dict:
        conversation.target_ai = target
        return architect.finish(conversation)

    try:
        await _run_step(callback.message, state, rebuild)
        await state.update_data(target_ai=target)
    except Exception:
        logger.exception("Could not retarget prompt in chat %s", callback.message.chat.id)
        await callback.message.answer(messages.UNEXPECTED, reply_markup=final_keyboard())


@router.callback_query()
async def stale_callback(callback: CallbackQuery) -> None:
    # Buttons from an old message or another step; answer so the client stops the spinner.
    await callback.answer(messages.STALE_BUTTON, show_alert=True)


# --- References: photos, files and forwarded messages, accepted at any step ---

async def _prepare_reference_state(message: Message, state: FSMContext) -> str:
    """Materials sent before /start or after a finished prompt begin a new prompt."""
    async with _locks[_key(state)]:
        current = await state.get_state()
        if current in (None, PromptStates.completed.state):
            await state.clear()
            await state.set_state(PromptStates.waiting_for_target)
            current = PromptStates.waiting_for_target.state
        return current


def _next_step(current: str):
    if current == PromptStates.waiting_for_target.state:
        return messages.REFERENCE_NEXT_TARGET, target_ai_keyboard()
    if current == PromptStates.waiting_for_mode.state:
        return messages.REFERENCE_NEXT_MODE, mode_keyboard()
    if current == PromptStates.clarifying.state:
        return messages.REFERENCE_NEXT_CLARIFY, None
    return messages.REFERENCE_NEXT_REQUEST, None


async def _acknowledge(message: Message, state: FSMContext, current: str, label: str, count: int) -> None:
    text, markup = _next_step(current)
    text = messages.REFERENCE_SAVED.format(label=html.escape(label), count=count) + "\n\n" + text
    caption = (message.caption or "").strip()
    if caption and current == PromptStates.waiting_for_request.state and not is_taskless(caption):
        await state.update_data(pending_task=caption)
        text += messages.REFERENCE_CAPTION_HINT
        markup = caption_keyboard()
    group = message.media_group_id
    if group and group in _album_acks:
        with suppress(TelegramBadRequest):
            await _album_acks[group].edit_text(text, reply_markup=markup)
        return
    ack = await message.answer(text, reply_markup=markup)
    if group:
        if len(_album_acks) > 500:
            _album_acks.clear()
        _album_acks[group] = ack


async def _store_reference(message: Message, state: FSMContext, label: str, reference: str) -> None:
    current = await state.get_state()
    count = await _add_reference(state, reference)
    if count is None:
        await message.answer(messages.REFERENCE_LIMIT.format(limit=MAX_REFERENCES))
        return
    async with _ack_locks[_key(state)]:
        await _acknowledge(message, state, current, label, count)


async def _read_file(
    message: Message, state: FSMContext, architect: PromptArchitect,
    file, kind: str, mime_type: str, label: str,
) -> None:
    if (file.file_size or 0) > MAX_FILE_BYTES:
        await message.answer(messages.REFERENCE_TOO_BIG)
        return
    await _prepare_reference_state(message, state)
    key = _key(state)
    note = (message.caption or "").strip()
    _pending[key] += 1
    try:
        async with _typing(message):
            data = (await message.bot.download(file)).read()
            if kind == "text":
                body = decode_text(data)
            else:
                body = await asyncio.to_thread(architect.analyze_reference, data, mime_type, note)
        if not body:
            raise ValueError("empty reference")
    except Exception:
        logger.exception("Could not read reference in chat %s", message.chat.id)
        await message.answer(messages.REFERENCE_FAILED)
        return
    finally:
        _pending[key] -= 1
    await _store_reference(message, state, label, format_reference(label, body, note))


@router.message(F.photo)
async def receive_photo(message: Message, state: FSMContext, architect: PromptArchitect) -> None:
    label = "Rasm" + (f": {message.caption.strip()[:40]}" if message.caption else "")
    await _read_file(message, state, architect, message.photo[-1], "media", "image/jpeg", label)


@router.message(F.document)
async def receive_document(message: Message, state: FSMContext, architect: PromptArchitect) -> None:
    document = message.document
    kind = document_kind(document.file_name, document.mime_type)
    if kind is None:
        await message.answer(messages.REFERENCE_UNSUPPORTED)
        return
    name = document.file_name or "hujjat"
    if document.mime_type == "application/pdf":
        label = f"PDF: {name}"
    elif kind == "media":
        label = f"Rasm: {name}"
    else:
        label = f"Fayl: {name}"
    await _read_file(message, state, architect, document, kind, document.mime_type or "", label)


@router.message(F.forward_origin, F.text)
async def receive_forwarded_text(message: Message, state: FSMContext) -> None:
    current = await _prepare_reference_state(message, state)
    if current == PromptStates.waiting_for_reference.state:
        await receive_text_reference(message, state)
        return
    text = message.text.strip()
    label = f"Forward: {text[:40]}"
    await _store_reference(message, state, label, format_reference(label, text))


@router.message(PromptStates.waiting_for_reference, F.text)
async def receive_text_reference(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    label = f"Matn: {text[:40]}"
    count = await _add_reference(state, format_reference(label, text))
    if count is None:
        await message.answer(messages.REFERENCE_LIMIT.format(limit=MAX_REFERENCES))
    else:
        await message.answer(messages.REFERENCE_SAVED.format(label=html.escape(label), count=count))
    await _return_from_reference(message, state)


@router.message(F.voice | F.audio | F.video | F.video_note | F.sticker | F.animation)
async def unsupported_reference(message: Message) -> None:
    await message.answer(messages.REFERENCE_UNSUPPORTED)


# --- Text for each step ---

@router.message(PromptStates.waiting_for_request, F.text)
async def receive_request(message: Message, state: FSMContext, architect: PromptArchitect) -> None:
    await _start_request(message, state, architect, message.text.strip())


@router.message(PromptStates.waiting_for_mode)
async def mode_must_be_button(message: Message) -> None:
    await message.answer(messages.PRESS_BUTTON, reply_markup=mode_keyboard())


@router.message(PromptStates.clarifying, F.text)
async def receive_answer(message: Message, state: FSMContext, architect: PromptArchitect) -> None:
    answer = message.text
    try:
        await _run_step(message, state, lambda c: architect.answer(c, answer))
    except Exception:
        logger.exception("Could not process clarification answer in chat %s", message.chat.id)
        await message.answer(messages.UNEXPECTED)


@router.message(PromptStates.completed, F.text)
async def completed_message(message: Message) -> None:
    await message.answer(messages.WHAT_NEXT, reply_markup=final_keyboard())


@router.message(PromptStates.waiting_for_target)
async def target_must_be_button(message: Message) -> None:
    await message.answer(messages.CHOOSE_TARGET, reply_markup=target_ai_keyboard())


@router.message(StateFilter(None))
async def no_state_message(message: Message, state: FSMContext) -> None:
    # E.g. the bot restarted (MemoryStorage is lost) or the user never sent /start.
    await _show_target_selection(message, state)


@router.message()
async def text_only(message: Message) -> None:
    await message.answer(messages.TEXT_ONLY)

import json
import time
import unittest
from datetime import datetime
from itertools import count

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import GetFile, SendMessage
from aiogram.types import Chat, File, Message, Update, User

from architect import PromptArchitect
from bot import keyboards
from bot.handlers import router
from bot.references import decode_text, document_kind, format_reference, reference_label


class FakeAI:
    def __init__(self):
        self.calls = []

    def generate(self, instruction: str, context: str) -> str:
        time.sleep(0.02)  # a real API call takes time; lets the typing indicator start
        self.calls.append((instruction, context))
        if "Understanding Engine" in instruction:
            return json.dumps({"task_type": "design", "goal": "landing", "confidence": 0.9})
        if "Decision Engine" in instruction:
            return json.dumps({"decision": "ASK_CLARIFICATION", "questions": ["Rang?"]})
        if "Prompt Review Engine" in instruction:
            return json.dumps({"status": "READY", "issues": []})
        if "Final Prompt Builder" in instruction:
            return "FINAL PROMPT"
        raise AssertionError("Unexpected instruction")

    def describe(self, instruction, data, mime_type, note=""):
        self.calls.append(("describe", mime_type, note))
        return "A dark minimal landing page with a green button."


class FakeSession(BaseSession):
    """Records Bot API calls instead of talking to Telegram."""

    def __init__(self):
        super().__init__()
        self.requests = []
        self.ids = count(1000)

    async def make_request(self, bot, method, timeout=None):
        self.requests.append(method)
        if isinstance(method, SendMessage):
            return Message(
                message_id=next(self.ids), date=datetime.now(),
                chat=Chat(id=method.chat_id, type="private"), text=method.text,
            ).as_(bot)
        if isinstance(method, GetFile):
            return File(file_id=method.file_id, file_unique_id="u", file_size=3, file_path="photos/x.jpg")
        return True

    async def stream_content(self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True):
        yield b"img"

    async def close(self):
        pass


USER = User(id=1, is_bot=False, first_name="Ali")
CHAT = Chat(id=1, type="private")


class BotFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ai = FakeAI()
        self.session = FakeSession()
        self.bot = Bot("42:TEST", session=self.session)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.dp["architect"] = PromptArchitect(self.ai)
        self.dp.include_router(router)
        self.update_ids = count(1)

    async def asyncTearDown(self):
        # The router is module-level; detach it so the next test can include it again.
        router._parent_router = None

    async def send(self, **fields):
        message = Message(message_id=next(self.update_ids), date=datetime.now(), chat=CHAT, from_user=USER, **fields)
        await self.dp.feed_update(self.bot, Update(update_id=next(self.update_ids), message=message))

    async def press(self, data):
        from aiogram.types import CallbackQuery
        message = Message(message_id=1, date=datetime.now(), chat=CHAT, text="x")
        callback = CallbackQuery(id="c", from_user=USER, chat_instance="i", message=message, data=data)
        await self.dp.feed_update(self.bot, Update(update_id=next(self.update_ids), callback_query=callback))

    def sent_texts(self):
        return [m.text for m in self.session.requests if isinstance(m, SendMessage)]

    async def test_reference_before_task_is_used_in_final_prompt(self):
        from aiogram.types import PhotoSize
        await self.send(text="/start")
        await self.send(photo=[PhotoSize(file_id="p", file_unique_id="p", width=10, height=10)], caption="shu uslubda")
        self.assertIn("Qabul qilindi", self.sent_texts()[-1])
        await self.press("target:claude")
        await self.send(text="Kofe do'koni uchun landing sahifa")
        self.assertIn("3/3", self.sent_texts()[-1])
        await self.press("mode:CLARIFY")
        self.assertIn("Rang?", self.sent_texts()[-1])
        await self.press("finish_now")
        texts = self.sent_texts()
        self.assertTrue(any("FINAL PROMPT" in t for t in texts))
        builder_context = next(call[1] for call in self.ai.calls if "Final Prompt Builder" in call[0])
        self.assertIn("green button", builder_context)
        self.assertIn("shu uslubda", builder_context)
        self.assertIn("Claude", builder_context)
        actions = [m for m in self.session.requests if type(m).__name__ == "SendChatAction"]
        self.assertTrue(actions, "typing indicator was never sent")

    async def test_menu_button_wins_over_task_input(self):
        await self.send(text="/start")
        await self.press("target:chatgpt")
        await self.send(text=keyboards.MENU_HELP)
        self.assertIn("qo‘llanmasi", self.sent_texts()[-1])
        self.assertFalse(any("Understanding Engine" in c[0] for c in self.ai.calls))

    async def test_text_reference_then_regenerate_for_other_target(self):
        await self.send(text="/start")
        await self.press("target:gemini")
        await self.press("add_text_reference")
        await self.send(text="Rasmiy uslubda yoz")
        await self.send(text="Rezyume uchun prompt")
        await self.press("mode:ASSUME")
        await self.press("retarget:deepseek")
        contexts = [call[1] for call in self.ai.calls if "Final Prompt Builder" in call[0]]
        self.assertEqual(len(contexts), 2)
        self.assertIn("Rasmiy uslubda yoz", contexts[1])
        self.assertIn("DeepSeek", contexts[1])


class ReferenceHelperTests(unittest.TestCase):
    def test_document_kind(self):
        self.assertEqual(document_kind("a.pdf", "application/pdf"), "media")
        self.assertEqual(document_kind("notes.md", "application/octet-stream"), "text")
        self.assertEqual(document_kind("x.png", "image/png"), "media")
        self.assertIsNone(document_kind("a.docx", "application/vnd.openxmlformats"))

    def test_label_and_truncation(self):
        ref = format_reference("PDF: brief.pdf", "body", note="muhim")
        self.assertEqual(reference_label(ref), "PDF: brief.pdf")
        self.assertIn("User note: muhim", ref)
        self.assertIn("qisqartirildi", decode_text(b"a" * 20_000))


class FinishTests(unittest.TestCase):
    def test_finish_skips_remaining_questions(self):
        architect = PromptArchitect(FakeAI())
        state, _ = architect.begin("Bot kerak")
        self.assertEqual(architect.choose_mode(state, "CLARIFY")["status"], "NEED_CLARIFICATION")
        result = architect.finish(state)
        self.assertEqual(result["status"], "FINAL_PROMPT")
        self.assertEqual(state.current_questions, [])


if __name__ == "__main__":
    unittest.main()

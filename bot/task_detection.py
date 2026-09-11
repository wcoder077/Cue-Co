import re


_GREETINGS = {"salom", "assalom", "assalomu alaykum", "hello", "hi", "hey", "privet"}


def is_taskless(text: str) -> bool:
    """Block bare greetings, but permit a short actual request such as 'bot kerak'."""
    normalized = re.sub(r"[^\w\s]", "", text.lower()).strip()
    return not normalized or normalized in _GREETINGS

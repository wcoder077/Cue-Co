import json
import re


def extract_json(text: str) -> dict:

    text = text.strip()

    try:
        data = json.loads(text)

    except json.JSONDecodeError:
        # Models often wrap JSON in ```json fences or add prose around it.
        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )

        if not match:
            raise ValueError(
                "AI javobidan JSON topilmadi."
            )

        data = json.loads(match.group(0))

    if not isinstance(data, dict):
        raise ValueError(
            "AI javobidagi JSON obyekt emas."
        )

    return data


def as_list(value) -> list[str]:
    """Normalize an AI-provided field that should be a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]
import json
import re


def extract_json(text: str) -> dict:

    text = text.strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        pass

    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )

    if not match:
        raise ValueError(
            "AI javobidan JSON topilmadi."
        )

    return json.loads(match.group(0))
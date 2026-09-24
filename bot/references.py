"""Turn Telegram attachments into text references for the prompt pipeline."""

from pathlib import Path

MAX_REFERENCES = 10
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 12_000

TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".tsv", ".json", ".yaml", ".yml", ".xml", ".html", ".css",
    ".js", ".ts", ".tsx", ".jsx", ".py", ".java", ".kt", ".go", ".rs", ".c", ".h",
    ".cpp", ".cs", ".php", ".rb", ".swift", ".sql", ".sh", ".toml", ".ini", ".log",
}
# Formats Gemini can read directly as inline bytes.
MEDIA_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"}


def document_kind(file_name: str | None, mime_type: str | None) -> str | None:
    """Return "text", "media" or None (unsupported) for a Telegram document."""
    mime_type = (mime_type or "").lower()
    if mime_type in MEDIA_MIME_TYPES:
        return "media"
    if mime_type.startswith("text/") or Path(file_name or "").suffix.lower() in TEXT_EXTENSIONS:
        return "text"
    return None


def decode_text(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace").strip()
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS] + "\n[... fayl qisqartirildi ...]"
    return text


def format_reference(label: str, body: str, note: str = "") -> str:
    """First line is a short human label; /materials shows it."""
    parts = [f"[{label}]"]
    if note.strip():
        parts.append(f"User note: {note.strip()}")
    parts.append(body.strip())
    return "\n".join(parts)


def reference_label(reference: str, limit: int = 60) -> str:
    first = reference.strip().splitlines()[0] if reference.strip() else ""
    if first.startswith("[") and first.endswith("]"):
        return first[1:-1]
    return first if len(first) <= limit else first[:limit - 1] + "…"

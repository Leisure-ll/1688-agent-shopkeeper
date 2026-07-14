class MemoryCompressor:
    def __init__(self, max_chars: int = 600):
        self.max_chars = max_chars

    def compress(self, text: str) -> str:
        text = " ".join(text.split())
        if len(text) <= self.max_chars:
            return text
        return text[: self.max_chars - 3].rstrip() + "..."

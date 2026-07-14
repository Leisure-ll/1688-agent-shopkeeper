import hashlib
from pathlib import Path
from typing import Dict


class PromptRegistry:
    def __init__(self, prompt_dir: str = "prompts"):
        self.prompt_dir = Path(prompt_dir)

    def load(self, name: str) -> Dict[str, str]:
        path = self.prompt_dir / f"{name}.md"
        text = path.read_text(encoding="utf-8")
        return {"name": name, "version": hashlib.sha1(text.encode("utf-8")).hexdigest()[:8], "template": text}

    def render(self, name: str, **params: object) -> Dict[str, str]:
        prompt = self.load(name)
        text = prompt["template"]
        for key, value in params.items():
            text = text.replace("{{" + key + "}}", str(value))
        return {"name": prompt["name"], "version": prompt["version"], "text": text}

from pathlib import Path

PROMPT_VERSION = "v6"
_DIR = Path(__file__).parent


def load(name: str) -> str:
    return (_DIR / f"{name}_{PROMPT_VERSION}.txt").read_text()

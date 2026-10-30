from pathlib import Path

PROMPT_VERSION = "v2"
_DIR = Path(__file__).parent


def load(name: str) -> str:
    return (_DIR / f"{name}_{PROMPT_VERSION}.txt").read_text()

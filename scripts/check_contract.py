"""Fail when the running API and contracts/openapi.yaml disagree.

Checks (1) every documented method and path exists in the FastAPI app and vice versa, and (2) every error
code the backend raises is documented in the Error schema. Run from the repository root with the backend
dependencies installed:  cd backend && uv run python ../scripts/check_contract.py
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
METHODS = {"get", "post", "put", "patch", "delete"}


def normalize(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path.removeprefix("/api/v1")) or "/"


def routes(spec: dict) -> set[tuple[str, str]]:
    return {(m.upper(), normalize(p)) for p, item in spec["paths"].items() for m in item if m in METHODS}


def main() -> int:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import create_app

    contract = yaml.safe_load((ROOT / "contracts/openapi.yaml").read_text())
    live = create_app().openapi()
    documented, implemented = routes(contract), routes(live)
    problems = [f"documented but not implemented: {m} {p}" for m, p in sorted(documented - implemented)]
    problems += [f"implemented but not documented: {m} {p}" for m, p in sorted(implemented - documented)]

    enum = set(contract["components"]["schemas"]["Error"]["properties"]["error"]["properties"]["code"]["enum"])
    used = set()
    for source in (ROOT / "backend/app").rglob("*.py"):
        used |= set(re.findall(r'ApiError\(\s*\d+,\s*"([A-Z_]+)"', source.read_text()))
    problems += [f"error code raised but not in the Error enum: {c}" for c in sorted(used - enum)]

    for problem in problems:
        print("DRIFT:", problem)
    print(f"{len(documented)} documented routes, {len(implemented)} implemented, {len(used)} error codes in use.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

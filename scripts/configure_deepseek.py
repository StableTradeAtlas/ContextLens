from __future__ import annotations

from getpass import getpass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def main() -> None:
    key = getpass("DeepSeek API key: ").strip()
    if not key:
        raise SystemExit("No key entered; .env was not changed.")
    existing = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                name, value = line.split("=", 1)
                existing[name.strip()] = value.strip()
    existing["DEEPSEEK_API_KEY"] = key
    existing.setdefault("STABLETRADE_USE_DEEPSEEK", "1")
    existing.setdefault("DEEPSEEK_MODEL", "deepseek-chat")
    existing.setdefault("DEEPSEEK_TIMEOUT", "10")
    existing.setdefault("DEEPSEEK_MAX_TOKENS", "620")
    lines = [f"{name}={value}" for name, value in existing.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ENV_PATH.chmod(0o600)
    print("DeepSeek fast assist is configured in .env.")


if __name__ == "__main__":
    main()

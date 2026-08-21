from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser


PROJECT_ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PORT_ENV_KEYS = ("CONTEXTLENS_PORT", "STABLETRADE_PORT")


def configured_port() -> int:
    for key in PORT_ENV_KEYS:
        value = os.environ.get(key)
        if not value:
            continue
        try:
            return int(value)
        except ValueError:
            print(f"Ignoring invalid {key}={value!r}; using {DEFAULT_PORT}.")
            return DEFAULT_PORT
    return DEFAULT_PORT


def can_connect(port: int) -> bool:
    try:
        with socket.create_connection((HOST, port), timeout=0.35):
            return True
    except OSError:
        return False


def health_payload(port: int) -> dict:
    try:
        with urlopen(f"http://{HOST}:{port}/api/health", timeout=0.8) as response:
            if response.status != 200:
                return {}
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError):
        return {}


def is_contextlens_server(port: int) -> bool:
    payload = health_payload(port)
    return bool(payload.get("ok")) and "contextlens" in str(payload.get("version", "")).lower()


def choose_port(preferred: int) -> tuple[int, bool]:
    if is_contextlens_server(preferred):
        return preferred, True
    if not can_connect(preferred):
        return preferred, False
    for port in range(preferred + 1, preferred + 30):
        if not can_connect(port):
            return port, False
    raise RuntimeError("No available local port found near 8765.")


def prepare_environment(port: int) -> None:
    os.chdir(PROJECT_ROOT)
    sys.path.insert(0, str(PROJECT_ROOT))
    os.environ["CONTEXTLENS_PORT"] = str(port)
    os.environ["STABLETRADE_PORT"] = str(port)


def prepare_demo_index() -> None:
    from app.ingest import ingest

    report = ingest(use_live=False, seed_if_empty=True)
    print(
        "Prepared local evidence index: "
        f"{report.get('total_records', 0)} records "
        f"({report.get('inserted_official_snapshot', 0)} verified Shanghai Library snapshot upserts; "
        f"{report.get('inserted_seed', 0)} demo seed upserts)."
    )


def frontend_needs_build() -> bool:
    built_index = PROJECT_ROOT / "app" / "static" / "index.html"
    if not built_index.exists():
        return True
    watched = [
        PROJECT_ROOT / "frontend" / "index.html",
        PROJECT_ROOT / "frontend" / "vite.config.ts",
        PROJECT_ROOT / "package.json",
        PROJECT_ROOT / "package-lock.json",
    ]
    watched.extend((PROJECT_ROOT / "frontend" / "src").rglob("*"))
    newest_source = max((path.stat().st_mtime for path in watched if path.is_file()), default=0)
    return newest_source > built_index.stat().st_mtime


def prepare_frontend() -> None:
    if not frontend_needs_build():
        print("Frontend is ready.")
        return
    npm = shutil.which("npm")
    built_index = PROJECT_ROOT / "app" / "static" / "index.html"
    force_rebuild = os.environ.get("CONTEXTLENS_REBUILD_FRONTEND", "0").strip().lower() in {"1", "true", "yes", "on"}
    if built_index.exists() and not (PROJECT_ROOT / "node_modules").exists() and not force_rebuild:
        print("Using the packaged frontend (no Node.js installation required).")
        return
    if not npm:
        if built_index.exists():
            print("npm is unavailable; using the last built frontend.")
        else:
            print("npm is unavailable; using the built-in research interface.")
        return
    if not (PROJECT_ROOT / "node_modules").exists():
        print("Installing pinned frontend dependencies…")
        subprocess.run([npm, "ci", "--ignore-scripts"], cwd=PROJECT_ROOT, check=True)
    print("Building the updated frontend…")
    subprocess.run([npm, "run", "build"], cwd=PROJECT_ROOT, check=True)


def open_browser(port: int) -> None:
    enabled = os.environ.get("CONTEXTLENS_OPEN_BROWSER", "1").strip().lower()
    if enabled not in {"0", "false", "no", "off"}:
        webbrowser.open(f"http://{HOST}:{port}/")


def main() -> int:
    preferred_port = configured_port()
    port, already_running = choose_port(preferred_port)
    prepare_environment(port)

    url = f"http://{HOST}:{port}/"
    if already_running:
        print(f"ContextLens is already running at {url}")
        open_browser(port)
        return 0

    if port != preferred_port:
        print(f"Port {preferred_port} is busy; starting ContextLens on {port}.")

    prepare_frontend()
    prepare_demo_index()
    print(f"Starting ContextLens at {url}")
    print("Press Ctrl+C to stop.")

    threading.Timer(1.0, open_browser, args=(port,)).start()
    from app.memory_web import main as run_web_demo

    try:
        run_web_demo()
    except KeyboardInterrupt:
        print("\nContextLens stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# tools/system.py
import subprocess
import webbrowser
import os
from pathlib import Path


def open_app(app_name: str) -> str:
    """Open an application or website."""
    # check if it's a URL
    if app_name.startswith("http") or "." in app_name:
        webbrowser.open(app_name if app_name.startswith(
            "http") else f"https://{app_name}")
        return f"Opened {app_name} in your browser."

    # common app mappings for Windows
    apps = {
        "spotify": "spotify",
        "notepad": "notepad",
        "calculator": "calc",
        "explorer": "explorer",
        "chrome": "chrome",
        "discord": "discord",
        "vscode": "code",
        "terminal": "cmd",
    }

    app_key = app_name.lower()
    command = apps.get(app_key, app_name)

    try:
        subprocess.Popen(command, shell=True)
        return f"Opened {app_name}."
    except Exception as e:
        return f"Couldn't open {app_name}: {str(e)}"


def read_file(path: str) -> str:
    """Read a file and return its contents."""
    try:
        content = Path(path).read_text(encoding="utf-8")
        # truncate if massive
        if len(content) > 3000:
            content = content[:3000] + "\n... (truncated)"
        return content
    except Exception as e:
        return f"Couldn't read file: {str(e)}"


def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        Path(path).write_text(content, encoding="utf-8")
        return f"File written to {path}."
    except Exception as e:
        return f"Couldn't write file: {str(e)}"

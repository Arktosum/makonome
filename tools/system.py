# tools/system.py
import subprocess
import webbrowser
from tools.registry import tool

# Only apps on this allowlist can be launched — the model must never be able
# to execute arbitrary shell commands.
APPS = {
    "spotify": "spotify",
    "notepad": "notepad",
    "calculator": "calc",
    "explorer": "explorer",
    "chrome": "chrome",
    "discord": "discord",
    "vscode": "code",
    "terminal": "cmd",
}


@tool(
    description="Open an app (spotify, notepad, calculator, explorer, chrome, "
                "discord, vscode, terminal) or a website URL in the browser.",
    params={"app_name": {"type": "string", "description": "app name from the list, or a website URL/domain"}},
)
def open_app(app_name: str) -> str:
    """Open an allowlisted application or a website."""
    # website?
    if app_name.startswith("http") or "." in app_name:
        webbrowser.open(app_name if app_name.startswith("http") else f"https://{app_name}")
        return f"Opened {app_name} in your browser."

    command = APPS.get(app_name.lower())
    if not command:
        available = ", ".join(sorted(APPS))
        return f"I can't open '{app_name}' — I'm only allowed to open: {available}."

    try:
        subprocess.Popen(command, shell=True)
        return f"Opened {app_name}."
    except Exception as e:
        return f"Couldn't open {app_name}: {str(e)}"

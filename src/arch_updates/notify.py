from __future__ import annotations

import subprocess
import sys

from colorama import Fore

from arch_updates.utils import c

_LAST_NOTIF_IDS: dict[str, int] = {}


def _close_notification(notif_id: int) -> None:
    subprocess.run(
        ["gdbus", "call", "--session",
         "--dest", "org.freedesktop.Notifications",
         "--object-path", "/org/freedesktop/Notifications",
         "--method", "org.freedesktop.Notifications.CloseNotification",
         str(notif_id)],
        capture_output=True,
    )


def notify(
    app_name: str,
    summary: str,
    body: str,
    actions: list[tuple[str, str]] | None = None,
    icon: str | None = None,
) -> str | None:
    old_id = _LAST_NOTIF_IDS.get(app_name)
    if old_id is not None:
        _close_notification(old_id)
    cmd = ["notify-send", "--print-id", "--wait",
           "--app-name", app_name]
    if icon:
        cmd += ["--app-icon", icon]
    cmd += [summary, body]
    if actions:
        first_key, first_label = actions[0]
        cmd += ["--action", f"default={first_label}"]
        cmd += ["--action", f"{first_key}={first_label}"]
        for action_id, label in actions[1:]:
            cmd += ["--action", f"{action_id}={label}"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print(c("error:", Fore.RED),
              "desktop notifications unavailable — install libnotify",
              file=sys.stderr)
        return None

    if result.returncode != 0:
        return None

    lines = result.stdout.strip().splitlines()
    if not lines:
        return None

    try:
        _LAST_NOTIF_IDS[app_name] = int(lines[0])
    except ValueError:
        pass

    if len(lines) >= 2 and actions:
        action = lines[1]
        if action == "default":
            return actions[0][0]
        for action_id, _ in actions:
            if action == action_id:
                return action_id
    return None

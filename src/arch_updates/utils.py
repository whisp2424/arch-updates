from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence

from colorama import Fore, Style

from arch_updates.config import get_terminal


def c(text: str, *styles: str) -> str:
    return "".join(styles) + text + Style.RESET_ALL


def is_root() -> bool:
    return os.geteuid() == 0


def sudo_cmd(cmd: list[str]) -> list[str]:
    return cmd if is_root() else ["sudo", *cmd]


def run_step(description: str, cmd: list[str], sudo: bool = False, input: str | None = None) -> int:
    if sudo:
        cmd = sudo_cmd(cmd)
    print(c("==>", Fore.CYAN, Style.BRIGHT), c(description, Style.BRIGHT))
    try:
        result = subprocess.run(cmd, input=input, text=True)
    except FileNotFoundError:
        print(c("error:", Fore.RED), f"{cmd[0]} not found", file=sys.stderr)
        return 1
    if result.returncode != 0:
        print(c("error:", Fore.RED), f"{description.lower()} failed", file=sys.stderr)
    return result.returncode


def run_in_terminal(script_args: Sequence[str]) -> bool:
    if os.isatty(sys.stdout.fileno()) or os.environ.get("ARCH_MAINT_TERMINAL"):
        return False
    terminal = get_terminal()
    if terminal is None:
        print(c("error:", Fore.RED), "no terminal emulator configured", file=sys.stderr)
        print("  Set one in ~/.config/arch-updates/config.toml:", file=sys.stderr)
        print("    [terminal]", file=sys.stderr)
        print('    command = "ghostty"', file=sys.stderr)
        sys.exit(1)
    try:
        env = os.environ.copy()
        env["ARCH_MAINT_TERMINAL"] = "1"
        subprocess.run(
            [terminal, "-e", sys.executable, "-m", "arch_updates", *script_args],
            env=env,
            check=True,
        )
    except FileNotFoundError:
        print(c("error:", Fore.RED), f"terminal '{terminal}' not found", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError:
        print(c("error:", Fore.RED), f"terminal '{terminal}' exited with an error", file=sys.stderr)
        sys.exit(1)
    return True

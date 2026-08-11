from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from colorama import Fore, Style

from arch_updates.types import AurConfig

CACHE_DIR = Path.home() / ".cache" / "arch-updates"
NEWS_CACHE = CACHE_DIR / "news-read.json"
CONFIG_DIR = Path.home() / ".config" / "arch-updates"
CONFIG_FILE = CONFIG_DIR / "config.toml"

AUR_BUILTINS: dict[str, AurConfig] = {
    "paru": {
        "check_updates": ["paru", "-Qu"],
        "install_updates": ["paru", "-Sua"],
        "remove_orphans": ["paru", "-c", "--noconfirm"],
        "build_cache_dir": "paru",
    },
    "yay": {
        "check_updates": ["yay", "-Qu"],
        "install_updates": ["yay", "-Sua"],
        "remove_orphans": ["yay", "-Yc", "--noconfirm"],
        "build_cache_dir": "yay",
    },
}


def c(text: str, *styles: str) -> str:
    return str("".join(styles)) + text + str(Style.RESET_ALL)


_aur_config: AurConfig | None = None


def get_aur_config() -> AurConfig:
    global _aur_config
    if _aur_config is not None:
        return _aur_config

    conf = load_config().get("aur", {})
    helper = conf.get("helper", "auto")

    if helper == "auto":
        for name in AUR_BUILTINS:
            if subprocess.run(["which", name], capture_output=True).returncode == 0:
                _aur_config = AUR_BUILTINS[name]
                return _aur_config
        print(c("error:", Fore.RED), "no AUR helper found — install yay or paru", file=sys.stderr)
        sys.exit(1)

    if helper == "custom":
        required = ["check_updates", "install_updates", "remove_orphans", "build_cache_dir"]
        missing = [k for k in required if k not in conf]
        if missing:
            print(c("error:", Fore.RED),
                  f"missing keys in [aur] for custom helper: {', '.join(missing)}",
                  file=sys.stderr)
            sys.exit(1)
        for key in ("check_updates", "install_updates", "remove_orphans"):
            val = conf[key]
            if not isinstance(val, list) or not val or not all(isinstance(x, str) for x in val):
                print(c("error:", Fore.RED),
                      f"[aur].{key} must be a non-empty list of strings",
                      file=sys.stderr)
                sys.exit(1)
        if not isinstance(conf["build_cache_dir"], str) or not conf["build_cache_dir"]:
            print(c("error:", Fore.RED),
                  "[aur].build_cache_dir must be a non-empty string",
                  file=sys.stderr)
            sys.exit(1)
        if cmd := conf.get("command"):
            if not isinstance(cmd, str) or not cmd:
                print(c("error:", Fore.RED),
                      "[aur].command must be a non-empty string",
                      file=sys.stderr)
                sys.exit(1)
            _aur_config = AurConfig(
                check_updates=[cmd] + conf["check_updates"],
                install_updates=[cmd] + conf["install_updates"],
                remove_orphans=[cmd] + conf["remove_orphans"],
                build_cache_dir=conf["build_cache_dir"],
            )
        else:
            _aur_config = AurConfig(
                check_updates=conf["check_updates"],
                install_updates=conf["install_updates"],
                remove_orphans=conf["remove_orphans"],
                build_cache_dir=conf["build_cache_dir"],
            )
        return _aur_config

    print(c("error:", Fore.RED),
          f"invalid aur.helper '{helper}' — use 'auto' or 'custom'",
          file=sys.stderr)
    sys.exit(1)


def get_terminal() -> str | None:
    conf = load_config().get("terminal", {})
    if isinstance(conf, dict):
        cmd = conf.get("command")
    elif isinstance(conf, str):
        cmd = conf
    else:
        cmd = None
    return cmd or os.environ.get("TERMINAL")


def load_config() -> dict[str, Any]:
    try:
        return tomllib.loads(CONFIG_FILE.read_text())
    except (FileNotFoundError, tomllib.TOMLDecodeError, OSError):
        return {}


def save_config(data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(tomli_w.dumps(data))

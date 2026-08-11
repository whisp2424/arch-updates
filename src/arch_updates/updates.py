from __future__ import annotations

import subprocess
import sys

from colorama import Fore, Style

from arch_updates.config import get_aur_config, get_terminal, load_config
from arch_updates.news import get_unread_news
from arch_updates.notify import notify
from arch_updates.types import UpdateData
from arch_updates.utils import c, run_in_terminal, run_step


def get_update_data(
    no_pacman: bool = False,
    no_aur: bool = False,
    no_flatpak: bool = False,
) -> UpdateData:
    result: UpdateData = {
        "pacman_list": "",
        "aur_lines": [],
        "flatpak_list": "",
        "pacman_count": 0,
        "aur_count": 0,
        "flatpak_count": 0,
        "total": 0,
    }

    pacman_names: set[str] = set()
    if not no_pacman:
        try:
            pacman_r = subprocess.run(
                ["checkupdates"], capture_output=True, text=True, timeout=60,
            )
            pacman_list = pacman_r.stdout.strip()
            for line in pacman_list.splitlines():
                name = line.split()[0] if line else ""
                if name:
                    pacman_names.add(name)
        except subprocess.TimeoutExpired:
            print(c("error:", Fore.RED), "checkupdates timed out", file=sys.stderr)
            pacman_list = ""
    else:
        pacman_list = ""

    yay_names: set[str] = set()
    if not no_aur:
        try:
            yay_r = subprocess.run(
                get_aur_config()["check_updates"], capture_output=True, text=True, timeout=120,
            )
            yay_lines = yay_r.stdout.strip().splitlines()
            for line in yay_lines:
                name = line.split()[0] if line else ""
                if name:
                    yay_names.add(name)
        except FileNotFoundError:
            helper = get_aur_config()["check_updates"][0]
            print(c("error:", Fore.RED), f"AUR helper '{helper}' not found", file=sys.stderr)
            yay_lines = []
        except subprocess.TimeoutExpired:
            print(c("error:", Fore.RED), "AUR update check timed out", file=sys.stderr)
            yay_lines = []
    else:
        yay_lines = []

    aur_names = yay_names - pacman_names
    aur_lines: list[str] = []
    for name in sorted(aur_names):
        for line in yay_lines:
            if line.split() and line.split()[0] == name:
                aur_lines.append(line)
                break

    flatpak_list = ""
    if not no_flatpak:
        try:
            flatpak_r = subprocess.run(
                ["flatpak", "remote-ls", "--updates"],
                capture_output=True, text=True, timeout=60,
            )
            flatpak_list = flatpak_r.stdout.strip()
        except subprocess.TimeoutExpired:
            print(c("error:", Fore.RED), "flatpak update check timed out", file=sys.stderr)

    result["pacman_list"] = pacman_list
    result["aur_lines"] = aur_lines
    result["flatpak_list"] = flatpak_list
    result["pacman_count"] = len(pacman_list.splitlines()) if pacman_list else 0
    result["aur_count"] = len(aur_lines)
    result["flatpak_count"] = len(flatpak_list.splitlines()) if flatpak_list else 0
    result["total"] = result["pacman_count"] + result["aur_count"] + result["flatpak_count"]
    return result


def print_updates(data: UpdateData) -> None:
    if data["total"] == 0:
        print(c("::", Fore.CYAN, Style.BRIGHT), c("System is up to date", Style.BRIGHT))
        return

    print(c("==>", Fore.CYAN, Style.BRIGHT), c(f"{data['total']} updates available", Style.BRIGHT))
    print()

    first = True

    if data["pacman_count"]:
        if not first:
            print()
        first = False
        print(c("::", Fore.CYAN, Style.BRIGHT), c(f"pacman ({data['pacman_count']})", Style.BRIGHT))
        for line in data["pacman_list"].splitlines():
            print(f"  {line}")

    if data["aur_count"]:
        if not first:
            print()
        first = False
        print(c("::", Fore.CYAN, Style.BRIGHT), c(f"AUR ({data['aur_count']})", Style.BRIGHT))
        for line in data["aur_lines"]:
            print(f"  {line}")

    if data["flatpak_count"]:
        if not first:
            print()
        first = False
        fpc = data["flatpak_count"]
        print(c("::", Fore.CYAN, Style.BRIGHT), c(f"flatpak ({fpc})", Style.BRIGHT))
        for line in data["flatpak_list"].splitlines():
            print(f"  {line}")


def check_updates(
    no_pacman: bool = False,
    no_aur: bool = False,
    no_flatpak: bool = False,
) -> int:
    print(c("::", Fore.CYAN, Style.BRIGHT), c("Checking for updates...", Style.BRIGHT))
    data = get_update_data(no_pacman=no_pacman, no_aur=no_aur, no_flatpak=no_flatpak)
    print_updates(data)
    return 0


def do_update(no_cleanup: bool = False) -> int:
    if run_in_terminal(["update"]):
        return 0
    print(c("::", Fore.CYAN, Style.BRIGHT), c("Checking for updates...", Style.BRIGHT))
    data = get_update_data()
    print_updates(data)

    print()

    new_indices, _news_items = get_unread_news()
    if new_indices:
        plural = "s" if len(new_indices) > 1 else ""
        print()
        print(c("==>", Fore.CYAN, Style.BRIGHT),
              c(f"You have {len(new_indices)} unread news item{plural}", Style.BRIGHT))
        print("  ",
              c("News may announce required manual interventions"
                " or breaking changes.", Style.BRIGHT),
              "Read it before updating.")
        print()

    errors: list[str] = []

    if data["total"] == 0:
        print(c("==>", Fore.CYAN, Style.BRIGHT), c("No updates to apply", Style.BRIGHT))
    else:
        try:
            answer = input(
                c("::", Fore.CYAN, Style.BRIGHT)
                + " "
                + c("Proceed with update? [Y/n] ", Style.BRIGHT)
            )
        except KeyboardInterrupt:
            print()
            answer = "n"
        if answer.strip().lower() in ("n", "no"):
            print(c("::", Fore.CYAN, Style.BRIGHT), c("Update cancelled", Style.BRIGHT))
        else:
            aborted = False
            if data["pacman_count"] and not aborted:
                print()
                try:
                    rc = run_step("Updating official packages...",
                                  ["pacman", "-Syu", "--noconfirm"], sudo=True)
                    if rc != 0:
                        errors.append("official packages")
                except KeyboardInterrupt:
                    print()
                    errors.append("official packages")
                    aborted = True

            if data["flatpak_count"] and not aborted:
                print()
                try:
                    rc = run_step("Updating Flatpak packages...", ["flatpak", "update", "-y"])
                    if rc != 0:
                        errors.append("Flatpak packages")
                except KeyboardInterrupt:
                    print()
                    errors.append("Flatpak packages")
                    aborted = True

            if data["aur_count"] and not aborted:
                print()
                print(c("==>", Fore.CYAN, Style.BRIGHT),
                      c("Updating AUR packages...", Style.BRIGHT))
                print(c("AUR packages are community-maintained.",
                        Style.BRIGHT), "Review PKGBUILD changes before updating.")
                print()
                try:
                    rc = subprocess.run(get_aur_config()["install_updates"], text=True).returncode
                    if rc != 0:
                        errors.append("AUR packages")
                except KeyboardInterrupt:
                    print()
                    errors.append("AUR packages")
                    aborted = True
                print()

    if not no_cleanup:
        from arch_updates.cleanup import do_cleanup
        config = load_config().get("cleanup", {})
        rc = do_cleanup(
            keep=config.get("keep"),
            dry_run=config.get("dry_run", False),
            no_orphans=config.get("no_orphans", False),
            no_paccache=config.get("no_paccache", False),
            no_aurcache=config.get("no_aurcache", False),
            no_flatpak=config.get("no_flatpak", False),
            _from_update=True,
        )
        if rc != 0:
            errors.append("cleanup")
    else:
        print(c("==>", Fore.CYAN, Style.BRIGHT), c("Skipping cleanup", Style.BRIGHT))

    print()
    if errors:
        print(c("==>", Fore.CYAN, Style.BRIGHT), c("Errors occurred during update", Style.BRIGHT))
    else:
        print(c("==>", Fore.CYAN, Style.BRIGHT), c("No errors occurred", Style.BRIGHT))
    if sys.stdin.isatty():
        print(c("::", Fore.CYAN, Style.BRIGHT), c("Press Enter to finish...", Style.BRIGHT))
        input()
    return 1 if errors else 0


def do_check(
    no_pacman: bool = False,
    no_aur: bool = False,
    no_flatpak: bool = False,
) -> int:
    if get_terminal() is None:
        print(c("error:", Fore.RED), "a terminal emulator must be configured", file=sys.stderr)
        return 1

    print(c("::", Fore.CYAN, Style.BRIGHT), c("Checking for updates...", Style.BRIGHT))
    data = get_update_data(no_pacman=no_pacman, no_aur=no_aur, no_flatpak=no_flatpak)
    print_updates(data)

    if data["total"] == 0:
        return 0

    action = notify(
        "System Updates", "Updates are available",
        f"{data['total']} packages can be updated",
        actions=[("open", "Update System")],
        icon="software-update-available-symbolic",
    )
    if action in ("default", "open"):
        terminal = get_terminal()
        if terminal:
            subprocess.Popen(
                [terminal, "-e", sys.executable, "-m", "arch_updates", "update"],
            )
    return 0

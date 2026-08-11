from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from colorama import Fore, Style

from arch_updates.config import get_aur_config, load_config, save_config
from arch_updates.utils import c, run_in_terminal, run_step


def do_cleanup(
    keep: int | None = None,
    dry_run: bool | None = None,
    no_orphans: bool | None = None,
    no_paccache: bool | None = None,
    no_aurcache: bool | None = None,
    no_flatpak: bool | None = None,
    save: bool = False,
    _from_update: bool = False,
) -> int:
    if not _from_update and run_in_terminal(["cleanup"]):
        return 0

    conf = load_config().get("cleanup", {})
    if keep is None:
        keep = conf.get("keep", 3)
    if no_orphans is None:
        no_orphans = conf.get("no_orphans", False)
    if no_paccache is None:
        no_paccache = conf.get("no_paccache", False)
    if no_aurcache is None:
        no_aurcache = conf.get("no_aurcache", False)
    if no_flatpak is None:
        no_flatpak = conf.get("no_flatpak", False)

    errors: list[str] = []

    if not no_orphans:
        result = subprocess.run(["pacman", "-Qdtq"], capture_output=True, text=True)
        orphans = [p for p in result.stdout.splitlines() if p]
        if not orphans:
            print(c("==>", Fore.CYAN, Style.BRIGHT), c("No orphaned packages", Style.BRIGHT))
        elif dry_run:
            print(c("==>", Fore.CYAN, Style.BRIGHT), c("Orphaned packages:", Style.BRIGHT))
            for pkg in orphans:
                print(f"  {pkg}")
        else:
            rc = run_step(
                "Removing orphaned packages...",
                get_aur_config()["remove_orphans"],
                input="\n".join(orphans),
            )
            if rc != 0:
                errors.append("orphan removal")
        print()
    else:
        print(c("==>", Fore.CYAN, Style.BRIGHT), c("Skipping orphan removal", Style.BRIGHT))
        print()

    if not no_paccache:
        cmd = ["paccache", "-rk", str(keep)]
        if dry_run:
            cmd.append("--dryrun")
        rc = run_step("Cleaning pacman cache...", cmd)
        if rc != 0:
            errors.append("pacman cache")
        print()
    else:
        print(c("==>", Fore.CYAN, Style.BRIGHT), c("Skipping pacman cache cleaning", Style.BRIGHT))
        print()

    if not no_aurcache:
        aur_cache_path = Path.home() / ".cache" / get_aur_config()["build_cache_dir"]
        if aur_cache_path.exists():
            print(c("==>", Fore.CYAN, Style.BRIGHT), c("Cleaning AUR build cache...", Style.BRIGHT))
            if not dry_run:
                subprocess.run(["rm", "-rf", str(aur_cache_path)])
        else:
            print(c("==>", Fore.CYAN, Style.BRIGHT), c("Cleaning AUR build cache...", Style.BRIGHT))
            print(c("==>", Fore.CYAN, Style.BRIGHT), c("Nothing to clean", Style.BRIGHT))
        print()
    else:
        print(c("==>", Fore.CYAN, Style.BRIGHT),
              c("Skipping AUR build cache cleaning", Style.BRIGHT))
        print()

    if not no_flatpak:
        print(c("==>", Fore.CYAN, Style.BRIGHT),
              c("Cleaning unused Flatpak runtimes...", Style.BRIGHT))
        if shutil.which("flatpak"):
            if not dry_run:
                result = subprocess.run(["flatpak", "uninstall", "--unused", "--noninteractive"],
                                         capture_output=True, text=True, timeout=60)
                output = result.stdout.strip()
                if output:
                    print(output)
                if result.returncode != 0:
                    errors.append("flatpak unused refs")
        else:
            print("  Flatpak not installed")
        print()
    else:
        print(c("==>", Fore.CYAN, Style.BRIGHT), c("Skipping Flatpak cleanup", Style.BRIGHT))
        print()

    if save:
        cfg = load_config()
        cfg["cleanup"] = {"keep": keep,
                          "no_orphans": no_orphans, "no_paccache": no_paccache,
                          "no_aurcache": no_aurcache, "no_flatpak": no_flatpak}
        save_config(cfg)

    if not _from_update:
        if errors:
            print(c("==>", Fore.CYAN, Style.BRIGHT), c("Errors occurred during cleanup", Style.BRIGHT))
        else:
            print(c("==>", Fore.CYAN, Style.BRIGHT), c("No errors occurred", Style.BRIGHT))
    if not _from_update and sys.stdin.isatty():
        print(c("::", Fore.CYAN, Style.BRIGHT), c("Press Enter to finish...", Style.BRIGHT))
        input()
    return 1 if errors else 0

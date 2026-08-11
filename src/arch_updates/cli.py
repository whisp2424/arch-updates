from __future__ import annotations

import sys

from colorama import Fore, Style

from arch_updates import __version__
from arch_updates.cleanup import do_cleanup
from arch_updates.config import NEWS_CACHE, get_terminal, load_config, save_config
from arch_updates.news import do_news, do_news_log
from arch_updates.updates import check_updates, do_check, do_update
from arch_updates.utils import c


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        add_help=False,
        description="Manage Arch Linux updates, cleanup tasks, and news checks",
    )

    parser.add_argument("-h", "--help", action="help",
                        help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=__version__)

    sub = parser.add_subparsers(dest="command", required=True)

    p_update = sub.add_parser(
        "update",
        add_help=False,
        help="Update packages and perform cleanup",
        description=(
            "Synchronize and upgrade all packages (pacman, AUR, flatpak),"
            " then remove orphaned dependencies and clean package caches"
        ),
    )
    p_update.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    p_update.add_argument("--no-cleanup", action="store_true",
                          help="Skip cleanup after updating")
    p_update.add_argument("--save", action="store_true",
                          help="Save current options as defaults")

    p_cleanup = sub.add_parser(
        "cleanup",
        add_help=False,
        help="Remove orphaned packages, clean cache, and delete leftovers",
        description=(
            "Remove orphaned packages, trim pacman cache, wipe AUR build"
            " cache, and clean unused Flatpak runtimes with configurable"
            " behavior and dry-run support"
        ),
    )
    p_cleanup.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    p_cleanup.add_argument("-k", "--keep", type=int, default=None, metavar="N",
                           help="Keep N versions in pacman cache (default: 3)")
    p_cleanup.add_argument("-d", "--dry-run", action="store_true", default=None,
                           help="Show what would be cleaned without deleting")
    p_cleanup.add_argument("--no-orphans", action="store_true", default=None,
                           help="Skip orphaned package removal")
    p_cleanup.add_argument("--no-paccache", action="store_true", default=None,
                           help="Skip pacman cache cleaning")
    p_cleanup.add_argument("--no-aurcache", action="store_true", default=None,
                            help="Skip AUR build cache cleaning")
    p_cleanup.add_argument("--no-flatpak", action="store_true", default=None,
                            help="Skip unused Flatpak runtime cleanup")
    p_cleanup.add_argument("--save", action="store_true",
                           help="Save current options as defaults")

    p_check = sub.add_parser(
        "check",
        add_help=False,
        help="Check for available updates",
        description=(
            "Query pacman, AUR helper, and flatpak for available package"
            " updates and display a summary grouped by source"
        ),
    )
    p_check.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    p_check.add_argument("-n", "--notify", action="store_true",
                         help="Notify about available updates")
    p_check.add_argument("--no-pacman", action="store_true", default=None,
                         help="Skip checking pacman updates")
    p_check.add_argument("--no-aur", action="store_true", default=None,
                         help="Skip checking AUR updates")
    p_check.add_argument("--no-flatpak", action="store_true", default=None,
                         help="Skip checking flatpak updates")
    p_check.add_argument("--save", action="store_true",
                         help="Save current options as defaults")

    p_news = sub.add_parser(
        "news",
        add_help=False,
        help="Check for new Arch Linux news",
        description=(
            "Fetch the Arch Linux RSS feed and display a paginated,"
            " colorized log of news items with titles, dates, links,"
            " and summaries"
        ),
    )
    p_news.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    p_news.add_argument("-c", "--count", type=int, default=None,
                        help="Number of news items to show (default: 3)")
    p_news.add_argument("-r", "--reverse",
                        action=argparse.BooleanOptionalAction, default=None,
                        help="Show news in reverse order (oldest first)")
    p_news.add_argument("--pager", choices=("auto", "always", "never"),
                        default=None,
                        help="Control pager behavior (default: never)")
    p_news.add_argument("-n", "--notify", action="store_true",
                        help="Notify about available news")
    p_news.add_argument("--clear-cache", action="store_true",
                        help="Clear cached read news and exit")
    p_news.add_argument("--read", choices=("always", "ask"),
                        default=None,
                        help="Mark news as read (default: ask)")
    p_news.add_argument("--unread", action=argparse.BooleanOptionalAction,
                        default=None,
                        help="Show only unread news (default: true)")
    p_news.add_argument("--save", action="store_true",
                         help="Save current options as defaults")

    p_config = sub.add_parser(
        "config",
        add_help=False,
        help="View or modify configuration settings",
        description="View or modify persistent configuration values",
    )
    p_config.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)

    config_sub = p_config.add_subparsers(dest="config_action")

    p_config_terminal = config_sub.add_parser(
        "terminal",
        add_help=False,
        help="Get or set the terminal emulator command",
        description=(
            "Display the currently configured terminal emulator,"
            " or set it to a new value"
        ),
    )
    p_config_terminal.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    p_config_terminal.add_argument(
        "command", nargs="?", default=None,
        metavar="COMMAND",
        help="Terminal emulator command (e.g. ghostty, kitty, foot)",
    )

    try:
        args = parser.parse_args()
    except KeyboardInterrupt:
        sys.exit(130)

    try:
        if args.command == "check":
            cfg_check = load_config().get("check", {})
            no_pacman = (
                args.no_pacman if args.no_pacman is not None
                else cfg_check.get("no_pacman", False)
            )
            no_aur = (
                args.no_aur if args.no_aur is not None
                else cfg_check.get("no_aur", False)
            )
            no_flatpak = (
                args.no_flatpak if args.no_flatpak is not None
                else cfg_check.get("no_flatpak", False)
            )
            if no_pacman and no_aur and no_flatpak:
                parser.error("All update sources have been disabled — nothing to check")
            if args.save:
                cfg = load_config()
                cfg["check"] = {"no_pacman": no_pacman, "no_aur": no_aur, "no_flatpak": no_flatpak}
                save_config(cfg)
            if args.notify:
                sys.exit(do_check(no_pacman=no_pacman, no_aur=no_aur, no_flatpak=no_flatpak))
            else:
                sys.exit(check_updates(no_pacman=no_pacman, no_aur=no_aur, no_flatpak=no_flatpak))
        elif args.command == "cleanup":
            sys.exit(do_cleanup(
                keep=args.keep, dry_run=args.dry_run,
                no_orphans=args.no_orphans, no_paccache=args.no_paccache,
                no_aurcache=args.no_aurcache, no_flatpak=args.no_flatpak,
                save=args.save,
            ))
        elif args.command == "update":
            if args.save:
                cfg = load_config()
                cfg["update"] = {"no_cleanup": args.no_cleanup}
                save_config(cfg)
            sys.exit(do_update(no_cleanup=args.no_cleanup))
        elif args.command == "config":
            if args.config_action == "terminal":
                if args.command:
                    cfg = load_config()
                    cfg["terminal"] = {"command": args.command}
                    save_config(cfg)
                    print(c("::", Fore.CYAN, Style.BRIGHT),
                          c(f"Terminal emulator set to '{args.command}'", Style.BRIGHT))
                else:
                    current = get_terminal()
                    if current:
                        print(c("::", Fore.CYAN, Style.BRIGHT),
                              c(f"Current terminal emulator: {current}", Style.BRIGHT))
                    else:
                        print(c("error:", Fore.RED),
                              "no terminal emulator configured", file=sys.stderr)
                        print("  Set one with:", file=sys.stderr)
                        print(f"    {sys.argv[0]} config terminal <command>", file=sys.stderr)
                        sys.exit(1)
            else:
                p_config.print_help()
                sys.exit(1)
        elif args.command == "news" and args.clear_cache:
            NEWS_CACHE.unlink(missing_ok=True)
        elif args.command == "news" and args.notify:
            sys.exit(do_news())
        elif args.command == "news":
            sys.exit(do_news_log(
                count=args.count, reverse=args.reverse,
                pager_mode=args.pager, read_mode=args.read,
                unread=args.unread, save=args.save,
            ))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

from colorama import Fore, Style

from arch_updates.config import CACHE_DIR, NEWS_CACHE, load_config, save_config
from arch_updates.notify import notify
from arch_updates.types import NewsItem
from arch_updates.utils import c


def fetch_news_feed() -> bytes:
    try:
        with urllib.request.urlopen(
            "https://archlinux.org/feeds/news/", timeout=15,
        ) as resp:
            result: bytes = resp.read()
            return result
    except Exception as e:
        print(c("error:", Fore.RED), f"failed to fetch news feed: {e}", file=sys.stderr)
        raise


def strip_html(text: str) -> str:
    text = re.sub(r"</?(?:p|br|div|li|h[1-6])\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_news_feed(xml_data: bytes) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.iter("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            date_el = item.find("pubDate")
            if title_el is None or link_el is None:
                continue
            title = title_el.text or ""
            link = link_el.text or ""
            desc = ""
            if desc_el is not None and desc_el.text:
                desc = strip_html(desc_el.text)
            date_str = ""
            if date_el is not None and date_el.text:
                date_str = date_el.text.strip()
            items.append({"title": title, "link": link, "description": desc, "date": date_str})
    except ET.ParseError:
        pass
    return items


def get_unread_news() -> tuple[list[int], list[NewsItem]]:
    try:
        xml_data = fetch_news_feed()
    except Exception:
        return [], []

    items = parse_news_feed(xml_data)
    if not items:
        return [], items

    read_ids: set[str] = set()
    if NEWS_CACHE.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            read_ids = set(json.loads(NEWS_CACHE.read_text()))

    slugs = [item["link"].rstrip("/").rsplit("/", 1)[-1] for item in items]

    new_indices = [i for i in range(len(items)) if slugs[i] not in read_ids]

    if not read_ids and len(new_indices) > 1:
        new_indices = [0]

    return new_indices, items


def do_news() -> int:
    print(c("::", Fore.CYAN, Style.BRIGHT), c("Fetching latest news...", Style.BRIGHT))
    sys.stdout.flush()

    try:
        xml_data = fetch_news_feed()
    except Exception:
        return 1

    try:
        items = parse_news_feed(xml_data)
        if not items:
            print(c("::", Fore.CYAN, Style.BRIGHT), c("No news items found", Style.BRIGHT))
            return 0

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        read_ids: set[str] = set()
        if NEWS_CACHE.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                read_ids = set(json.loads(NEWS_CACHE.read_text()))

        slugs: list[str] = []
        for item in items:
            slug = item["link"].rstrip("/").rsplit("/", 1)[-1]
            slugs.append(slug)

        new_indices = [
            i for i in range(len(items)) if slugs[i] not in read_ids
        ]

        if not read_ids and len(new_indices) > 1:
            for i in range(1, len(items)):
                read_ids.add(slugs[i])
            new_indices = [0]

        if not new_indices:
            print(c("==>", Fore.CYAN, Style.BRIGHT), c("No unread news", Style.BRIGHT))
            return 0

        plural = "s" if len(new_indices) > 1 else ""
        print(c("::", Fore.CYAN, Style.BRIGHT),
              c(f"{len(new_indices)} unread news item{plural}", Style.BRIGHT))
        for i in new_indices:
            title = items[i]["title"]
            print(f"  {c(title, Style.BRIGHT)}")

        if len(new_indices) == 1:
            i = new_indices[0]
            desc = items[i]["description"].split("\n\n")[0].strip()
            action = notify(
                "System News", items[i]["title"], desc,
                actions=[("open", "Read full news"), ("dismiss", "Mark as read")],
                icon="application-rss+xml-symbolic",
            )
            if action in ("default", "open"):
                subprocess.run(["xdg-open", items[i]["link"]],
                               capture_output=True)
                read_ids.add(slugs[i])
            elif action == "dismiss":
                read_ids.add(slugs[i])
        else:
            action = notify(
                "System News", f"You have {len(new_indices)} unread news",
                "New news available",
                actions=[("open", "Read all"), ("dismiss", "Mark all as read")],
                icon="application-rss+xml-symbolic",
            )
            if action in ("default", "open"):
                subprocess.run(["xdg-open", "https://archlinux.org/news/"],
                               capture_output=True)
                read_ids.update(slugs[i] for i in new_indices)
            elif action == "dismiss":
                read_ids.update(slugs[i] for i in new_indices)

        NEWS_CACHE.write_text(json.dumps(sorted(read_ids)))
        return 0
    except Exception as e:
        print(c("error:", Fore.RED), f"news notification failed: {e}", file=sys.stderr)
        return 1


def do_news_log(
    count: int | None = None,
    reverse: bool | None = None,
    pager_mode: str | None = None,
    read_mode: str | None = None,
    unread: bool | None = None,
    save: bool = False,
) -> int:
    conf = load_config().get("news", {})
    if count is None:
        count = conf.get("count", 3)
    if pager_mode is None:
        pager_mode = conf.get("pager", "never")
    if reverse is None:
        reverse = conf.get("reverse", pager_mode == "never")
    if read_mode is None:
        read_mode = conf.get("read", "ask")
    if unread is None:
        unread = conf.get("unread", True)

    try:
        xml_data = fetch_news_feed()
    except Exception:
        return 1

    items = parse_news_feed(xml_data)
    if not items:
        return 0

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    read_ids: set[str] = set()
    if NEWS_CACHE.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            read_ids = set(json.loads(NEWS_CACHE.read_text()))

    if unread:
        items = [
            item for item in items
            if item["link"].rstrip("/").rsplit("/", 1)[-1] not in read_ids
        ]
        if not items:
            print("no unread news")
            return 0

    if count is not None:
        items = items[:count]
    if reverse:
        items = list(reversed(items))

    dim = Style.DIM
    cols = shutil.get_terminal_size().columns
    wrap_width = max(20, cols - 4)

    def build_output(paged: bool) -> str:
        lines: list[str] = []
        lines.append("")
        for i, item in enumerate(items):
            if i > 0 or not paged:
                if i > 0:
                    lines.append("")
                s = c("━" * (cols if not paged else 16), Fore.CYAN, Style.BRIGHT)
                lines.append(s)
                lines.append("")
            title = item["title"]
            if paged:
                lines.append(c(title, Fore.YELLOW, Style.BRIGHT))
            else:
                for line in textwrap.fill(c(title, Fore.YELLOW, Style.BRIGHT),
                                          width=wrap_width).split("\n"):
                    lines.append(f"  {line}")
            if item["date"]:
                try:
                    dt = datetime.strptime(item["date"][:25].strip(), "%a, %d %b %Y %H:%M:%S")
                    date_str = dt.strftime('%b %d, %Y')
                    if paged:
                        lines.append(c(date_str, dim))
                        lines.append("")
                    else:
                        for line in textwrap.fill(c(date_str, dim),
                                                  width=wrap_width).split("\n"):
                            lines.append(f"  {line}")
                except ValueError:
                    pass
            if not paged:
                lines.append("")
            link = item["link"]
            if paged:
                lines.append(c(link, Fore.CYAN))
            else:
                for line in textwrap.fill(c(link, Fore.CYAN),
                                          width=wrap_width).split("\n"):
                    lines.append(f"  {line}")
            lines.append("")
            if item["description"]:
                para = item["description"].split("\n\n")[0].strip()
                if len(para) > 600:
                    para = para[:600] + "..."
                if paged:
                    lines.append(para)
                else:
                    wrapped = textwrap.fill(para, width=wrap_width,
                                            initial_indent="  ",
                                            subsequent_indent="  ")
                    for line in wrapped.split("\n"):
                        lines.append(line)
        if items and not paged:
            lines.append("")
            lines.append(c("━" * cols, Fore.CYAN, Style.BRIGHT))
        lines.append("")
        return "\n".join(lines)

    viewed = False

    if os.isatty(sys.stdout.fileno()):
        pager = os.environ.get("PAGER")
        if not pager:
            try:
                pager = shutil.which("less") or "less"
            except Exception:
                pager = None
        should_page = pager_mode == "always"
        output_plain: str | None = None
        if pager_mode == "auto" and pager:
            output_plain = build_output(paged=True)
            total_lines = len(output_plain.splitlines())
            _, rows = shutil.get_terminal_size()
            should_page = total_lines >= rows
        if should_page and pager:
            if output_plain is None:
                output_plain = build_output(paged=True)
            try:
                subprocess.run([pager], input=output_plain, text=True)
                viewed = True
            except FileNotFoundError:
                pass

    if not viewed:
        print(build_output(paged=False))

    unread_slugs: set[str] = set()
    for item in items:
        slug = item["link"].rstrip("/").rsplit("/", 1)[-1]
        if slug not in read_ids:
            unread_slugs.add(slug)

    if unread_slugs:
        if read_mode == "always":
            mark_read = True
        else:
            try:
                answer = input(
                    c("::", Fore.CYAN, Style.BRIGHT)
                    + " "
                    + c("Mark these news as read? [Y/n] ", Style.BRIGHT)
                )
            except KeyboardInterrupt:
                print()
                mark_read = False
            else:
                mark_read = answer.strip().lower() not in ("n", "no")

        if mark_read:
            read_ids.update(unread_slugs)
            NEWS_CACHE.write_text(json.dumps(sorted(read_ids)))

    if save:
        cfg = load_config()
        cfg["news"] = {"count": count, "reverse": reverse,
                       "pager": pager_mode, "read": read_mode,
                       "unread": unread}
        save_config(cfg)
    return 0

from __future__ import annotations

from typing import TypedDict


class AurConfig(TypedDict):
    check_updates: list[str]
    install_updates: list[str]
    remove_orphans: list[str]
    build_cache_dir: str


class UpdateData(TypedDict):
    pacman_list: str
    aur_lines: list[str]
    flatpak_list: str
    pacman_count: int
    aur_count: int
    flatpak_count: int
    total: int


class NewsItem(TypedDict):
    title: str
    link: str
    description: str
    date: str

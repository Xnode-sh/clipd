#!/data/data/com.termux/files/usr/bin/python3
# clipd — Clipboard Intelligence Daemon (TUI)
# Copyright (c) 2026 Xnode-sh — RED └•TEAM•┐ lab™
# SPDX-License-Identifier: MIT
import sqlite3
import curses
import json
import subprocess
import sys
from pathlib import Path

DB_PATH = Path.home() / "clipd" / "clipd.db"

TYPE_ICONS = {
    "url": "🔗", "email": "📧", "phone": "📞", "ipv4": "🌐",
    "uuid": "🆔", "ulid": "🆔", "jwt": "🔐", "base64": "📦",
    "hex_color": "🎨", "btc": "₿", "eth": "Ξ", "sol": "◎", "trx": "🔷",
    "md5": "🔐", "sha1": "🔐", "sha256": "🔐", "sha512": "🔐",
    "coords": "📍", "inn": "🆔", "snils": "🆔", "card": "💳",
    "tracking_ru": "📦", "tracking_cdek": "📦",
    "long_text": "📄", "text": "📝", "empty": "⌀",
}

def get_clips(filter_type=None, search="", limit=200):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        q = "SELECT * FROM clips WHERE 1=1"
        params = []
        if filter_type:
            q += " AND type LIKE ?"
            params.append(f"{filter_type}%")
        if search:
            q += " AND content LIKE ?"
            params.append(f"%{search}%")
        q += " ORDER BY pinned DESC, created_at DESC LIMIT ?"
        params.append(limit)
        return con.execute(q, params).fetchall()

def format_clip(row):
    icon = TYPE_ICONS.get(row["type"].split(":")[0], "📋")
    content = row["content"].replace("\n", " ↵ ")[:80]
    meta = json.loads(row["meta"]) if row["meta"] else {}
    pin = "📌" if row["pinned"] else ""
    dt = row["created_at"][:16].replace("T", " ")
    return f"{icon} {pin} [{dt}] {content}"

def draw(stdscr, clips, selected, filter_type, search, offset):
    h, w = stdscr.getmaxyx()
    stdscr.erase()
    stdscr.addstr(0, 0, f" clipd  |  filter: {filter_type or 'all'}  |  search: {search}".ljust(w), curses.A_REVERSE)

    visible = h - 3
    for i in range(visible):
        idx = offset + i
        if idx >= len(clips):
            break
        row = clips[idx]
        line = format_clip(row)
        attr = curses.A_REVERSE if idx == selected else curses.A_NORMAL
        try:
            stdscr.addstr(i + 1, 0, line[:w-1], attr)
        except curses.error:
            pass

    help_line = "↑↓ nav | Enter copy | p pin | d delete | / search | t filter | q quit"
    stdscr.addstr(h-1, 0, help_line[:w-1], curses.A_DIM)
    stdscr.refresh()

def main(stdscr):
    curses.curs_set(0)
    curses.use_default_colors()
    stdscr.keypad(True)

    clips = get_clips()
    selected = 0
    offset = 0
    filter_type = None
    search = ""

    while True:
        clips = get_clips(filter_type, search)
        if selected >= len(clips):
            selected = max(0, len(clips) - 1)
        if selected < offset:
            offset = selected
        elif selected >= offset + stdscr.getmaxyx()[0] - 3:
            offset = selected - stdscr.getmaxyx()[0] + 4

        draw(stdscr, clips, selected, filter_type, search, offset)

        key = stdscr.getch()

        if key == curses.KEY_UP and selected > 0:
            selected -= 1
        elif key == curses.KEY_DOWN and selected < len(clips) - 1:
            selected += 1
        elif key == ord('q'):
            break
        elif key == ord('p') and clips:
            row = clips[selected]
            with sqlite3.connect(DB_PATH) as con:
                con.execute("UPDATE clips SET pinned = NOT pinned WHERE id = ?", (row["id"],))
        elif key == ord('d') and clips:
            row = clips[selected]
            with sqlite3.connect(DB_PATH) as con:
                con.execute("DELETE FROM clips WHERE id = ?", (row["id"],))
            if selected >= len(clips) - 1:
                selected = max(0, len(clips) - 2)
        elif key == ord('/'):
            curses.echo()
            stdscr.addstr(0, 0, " search: ".ljust(stdscr.getmaxyx()[1]), curses.A_REVERSE)
            search = stdscr.getstr(0, 9, 60).decode("utf-8")
            curses.noecho()
            selected = 0
            offset = 0
        elif key == ord('t'):
            curses.echo()
            stdscr.addstr(0, 0, " filter (url, code, jwt, base64, etc): ".ljust(stdscr.getmaxyx()[1]), curses.A_REVERSE)
            filter_type = stdscr.getstr(0, 39, 30).decode("utf-8") or None
            curses.noecho()
            selected = 0
            offset = 0
        elif key in (curses.KEY_ENTER, 10, 13) and clips:
            row = clips[selected]
            content = row["content"]
            subprocess.run(["termux-clipboard-set", content])
            stdscr.addstr(0, 0, f" copied! ".ljust(stdscr.getmaxyx()[1]), curses.A_REVERSE | curses.A_BOLD)
            stdscr.refresh()
            curses.napms(500)

if __name__ == "__main__":
    if not DB_PATH.exists():
        print("Database not found. Run clipd.py first.")
        sys.exit(1)
    curses.wrapper(main)
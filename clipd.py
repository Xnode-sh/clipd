#!/data/data/com.termux/files/usr/bin/python3
# clipd — Clipboard Intelligence Daemon
# Copyright (c) 2026 Xnode-sh — RED └•TEAM•┐ lab™
# SPDX-License-Identifier: MIT
import sqlite3
import subprocess
import json
import re
import base64
import hashlib
import jwt
import html
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

DB_PATH = Path.home() / "clipd" / "clipd.db"

PATTERNS = {
    "url": re.compile(r"^https?://\S+$"),
    "email": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    "phone": re.compile(r"^(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$"),
    "ipv4": re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    "uuid": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I),
    "ulid": re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$"),
    "jwt": re.compile(r"^eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"),
    "tracking_ru": re.compile(r"^[A-Z]{2}\d{9}[A-Z]{2}$"),
    "inn": re.compile(r"^\d{10}$|^\d{12}$"),
    "snils": re.compile(r"^\d{3}-?\d{3}-?\d{3} ?\d{2}$"),
    "card": re.compile(r"^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$"),
    "btc": re.compile(r"^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}$"),
    "eth": re.compile(r"^0x[a-fA-F0-9]{40}$"),
    "sol": re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"),
    "trx": re.compile(r"^T[A-Za-z1-9]{33}$"),
    "md5": re.compile(r"^[a-f0-9]{32}$"),
    "sha1": re.compile(r"^[a-f0-9]{40}$"),
    "sha256": re.compile(r"^[a-f0-9]{64}$"),
    "sha512": re.compile(r"^[a-f0-9]{128}$"),
    "coords": re.compile(r"^-?\d{1,2}\.\d+,\s*-?\d{1,3}\.\d+$"),
    "hex_color": re.compile(r"^#?([0-9a-f]{3}|[0-9a-f]{6})$", re.I),
    "base64": re.compile(r"^[A-Za-z0-9+/]+={0,2}$"),
    "tracking_cdek": re.compile(r"^\d{10,20}$"),
}

LANG_PATTERNS = {
    "python": [r"^import\s+\w+", r"^def\s+\w+\s*\(", r"^class\s+\w+", r"^\s*@\w+", r"print\s*\("],
    "javascript": [r"^import\s+.*from", r"^const\s+\w+\s*=", r"^let\s+\w+\s*=", r"^function\s+\w+", r"console\.log", r"=>\s*\{"],
    "json": [r"^\s*\{", r"^\s*\[", r"^\s*\""],
    "sql": [r"(?i)^\s*(select|insert|update|delete|create|drop|alter)\s"],
    "bash": [r"^#!/(bin/)?bash", r"^\s*(cd|ls|cp|mv|rm|grep|awk|sed)\s", r"\$\("],
    "html": [r"^<!DOCTYPE html>", r"^<html", r"^<\w+.*>.*</\w+>"],
    "css": [r"^\s*\.\w+\s*\{", r"^\s*#\w+\s*\{", r"^\s*@media"],
    "yaml": [r"^\s*\w+:\s*", r"^\s*-\s+\w+"],
    "regex": [r"^/.+/[gimsuy]*$"],
}

TYPE_ICONS = {
    "url": "🔗", "email": "📧", "phone": "📞", "ipv4": "🌐",
    "uuid": "🆔", "ulid": "🆔", "jwt": "🔐", "base64": "📦",
    "hex_color": "🎨", "btc": "₿", "eth": "Ξ", "sol": "◎", "trx": "🔷",
    "md5": "🔐", "sha1": "🔐", "sha256": "🔐", "sha512": "🔐",
    "coords": "📍", "inn": "🆔", "snils": "🆔", "card": "💳",
    "tracking_ru": "📦", "tracking_cdek": "📦",
    "long_text": "📄", "text": "📝", "empty": "⌀",
}

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS clips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                meta TEXT,
                created_at TEXT NOT NULL,
                pinned INTEGER DEFAULT 0
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_clips_type ON clips(type)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_clips_created ON clips(created_at)")

def classify(text: str):
    text = text.strip()
    if not text:
        return "empty", {}

    for t, pat in PATTERNS.items():
        if pat.match(text):
            meta = extract_meta(t, text)
            return t, meta

    for lang, patterns in LANG_PATTERNS.items():
        for p in patterns:
            if re.search(p, text, re.MULTILINE):
                return f"code:{lang}", {"language": lang}

    if len(text) > 500:
        return "long_text", {"length": len(text)}
    return "text", {"length": len(text)}

def extract_meta(ctype: str, text: str):
    meta = {"raw": text[:500]}
    try:
        if ctype == "url":
            p = urlparse(text)
            meta = {"domain": p.netloc, "path": p.path, "params": p.query, "raw": text}
        elif ctype == "jwt":
            try:
                header = jwt.get_unverified_header(text)
                payload = jwt.decode(text, options={"verify_signature": False})
                meta = {"header": header, "payload": payload, "exp": payload.get("exp"), "raw": text}
            except Exception:
                meta = {"error": "invalid jwt", "raw": text}
        elif ctype == "base64":
            try:
                decoded = base64.b64decode(text + "==="[:(-len(text) % 4)]).decode("utf-8", errors="ignore")
                meta = {"decoded": decoded, "decoded_len": len(decoded), "raw": text}
            except Exception:
                meta = {"error": "decode failed", "raw": text}
        elif ctype == "hex_color":
            c = text.lstrip("#")
            if len(c) == 3:
                c = "".join(ch*2 for ch in c)
            r, g, b = int(c[0:2],16), int(c[2:4],16), int(c[4:6],16)
            meta = {"rgb": f"rgb({r},{g},{b})", "hsl": rgb_to_hsl(r,g,b), "raw": text}
        elif ctype == "coords":
            lat, lon = map(float, text.split(","))
            meta = {"lat": lat, "lon": lon, "maps_url": f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}", "raw": text}
        elif ctype in ("md5", "sha1", "sha256", "sha512"):
            meta = {"hash_type": ctype, "hash": text, "raw": text}
        elif ctype == "tracking_ru":
            meta = {"track_url": f"https://pochta.ru/tracking#{text}", "raw": text}
        elif ctype == "card":
            digits = re.sub(r"\D", "", text)
            meta = {"masked": f"**** **** **** {digits[-4:]}", "valid": luhn_check(digits), "raw": text}
        elif ctype.startswith("code:"):
            meta = {"language": ctype.split(":")[1], "raw": text}
        else:
            meta = {"raw": text}
    except Exception as e:
        meta = {"error": str(e), "raw": text}
    return meta

def rgb_to_hsl(r, g, b):
    r, g, b = r/255, g/255, b/255
    mx, mn = max(r,g,b), min(r,g,b)
    l = (mx + mn) / 2
    if mx == mn:
        h = s = 0
    else:
        d = mx - mn
        s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r: h = (g - b) / d + (6 if g < b else 0)
        elif mx == g: h = (b - r) / d + 2
        else: h = (r - g) / d + 4
        h /= 6
    return f"hsl({int(h*360)}, {int(s*100)}%, {int(l*100)}%)"

def luhn_check(num: str):
    try:
        return sum(int(d) if i % 2 == 0 else (int(d)*2 if int(d)*2 < 10 else int(d)*2 - 9)
                   for i, d in enumerate(reversed(num))) % 10 == 0
    except Exception:
        return False

def save_clip(content, ctype, meta):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO clips (content, type, meta, created_at) VALUES (?, ?, ?, ?)",
            (content, ctype, json.dumps(meta, ensure_ascii=False), datetime.now().isoformat())
        )

def build_notification(ctype, meta):
    raw = meta.get("raw", "")
    actions = []
    title = f"{TYPE_ICONS.get(ctype.split(':')[0], '📋')} Clipboard"
    content = raw[:80]

    if ctype == "url":
        domain = meta.get("domain", "")
        title = f"🔗 {domain}"
        content = meta.get("path", "")[:60]
        actions = [
            ("Открыть", f"termux-open-url '{raw}'"),
            ("Копировать домен", f"termux-clipboard-set '{domain}'"),
        ]
    elif ctype == "jwt":
        title = "🔐 JWT"
        exp = meta.get("exp")
        if exp:
            from datetime import datetime
            dt = datetime.fromtimestamp(exp)
            content = f"exp: {dt.strftime('%Y-%m-%d %H:%M')}"
        else:
            content = "no exp claim"
        actions = [
            ("Header → буфер", f"termux-clipboard-set '{json.dumps(meta.get('header', {}), ensure_ascii=False)}'"),
            ("Payload → буфер", f"termux-clipboard-set '{json.dumps(meta.get('payload', {}), ensure_ascii=False)}'"),
        ]
    elif ctype == "base64":
        title = "📦 Base64"
        decoded = meta.get("decoded", "")
        content = decoded[:80]
        actions = [
            ("Decoded → буфер", f"termux-clipboard-set '{html.escape(decoded)}'"),
        ]
    elif ctype == "hex_color":
        title = "🎨 Color"
        content = f"RGB: {meta.get('rgb')} | HSL: {meta.get('hsl')}"
        actions = [
            ("RGB → буфер", f"termux-clipboard-set '{meta.get('rgb')}'"),
            ("HSL → буфер", f"termux-clipboard-set '{meta.get('hsl')}'"),
        ]
    elif ctype in ("btc", "eth", "sol", "trx"):
        title = f"💰 {ctype.upper()}"
        content = meta.get("masked", "")[:50]
        actions = [
            ("Explorer", f"termux-open-url 'https://blockchain.com/search?search={raw}'"),
        ]
    elif ctype in ("md5", "sha1", "sha256", "sha512"):
        title = f"🔐 {ctype.upper()}"
        content = "Хеш обнаружен"
        actions = [
            ("VirusTotal", f"termux-open-url 'https://www.virustotal.com/gui/search/{raw}'"),
        ]
    elif ctype == "coords":
        title = "📍 Координаты"
        content = f"{meta.get('lat')}, {meta.get('lon')}"
        actions = [
            ("Organic Maps", f"termux-open-url 'geo:{meta.get('lat')},{meta.get('lon')}?q={meta.get('lat')},{meta.get('lon')}'"),
            ("OSM", f"termux-open-url '{meta.get('maps_url')}'"),
        ]
    elif ctype == "tracking_ru":
        title = "📦 Трек-номер"
        content = meta.get("track_url", "")
        actions = [
            ("Открыть трекинг", f"termux-open-url '{meta.get('track_url')}'"),
        ]
    elif ctype.startswith("code:"):
        lang = ctype.split(":")[1]
        title = f"💻 Code: {lang}"
        content = raw[:80]
        actions = [
            ("Копировать", f"termux-clipboard-set '{html.escape(raw)}'"),
        ]
    else:
        return None

    return title, content, actions

def send_notification(title, content, actions):
    if not actions:
        subprocess.run(["termux-toast", f"{title}: {content}"])
        return
    action_args = []
    for label, cmd in actions:
        action_args.extend(["--action", f"{label}:{cmd}"])
    subprocess.run([
        "termux-notification",
        "--id", "8842",
        "--title", title,
        "--content", content,
        "--priority", "high",
        "--ongoing",
        *action_args
    ])

def process_text(text: str):
    init_db()
    ctype, meta = classify(text)
    save_clip(text, ctype, meta)
    notif = build_notification(ctype, meta)
    if notif:
        title, cont, actions = notif
        send_notification(title, cont, actions)
    else:
        subprocess.run(["termux-toast", f"Saved: {ctype}"])
    print(f"[{ctype}] {text[:80]}")

def get_input_from_dialog():
    try:
        result = subprocess.run([
            "termux-dialog", "text",
            "-t", "clipd: вставьте текст",
            "-i", "",
            "-m"
        ], capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        return data.get("text", "").strip()
    except Exception:
        return ""

def get_input_from_share():
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()
    return ""

def main():
    text = get_input_from_share() or get_input_from_dialog()
    if not text:
        subprocess.run(["termux-toast", "No input"])
        return
    process_text(text)

if __name__ == "__main__":
    main()
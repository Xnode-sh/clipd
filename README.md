# clipd — Clipboard Intelligence Daemon

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Termux](https://img.shields.io/badge/platform-Termux-black.svg)](https://termux.dev)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab.svg)](https://www.python.org)
[![Android 10+](https://img.shields.io/badge/Android-10%2B-3ddc84.svg)](https://www.android.com)

Анализатор буфера обмена для Termux. Распознаёт 20+ типов данных и выдаёт контекстные действия через уведомление.

> Автор: **Xnode-sh** · RED └•TEAM•┐ lab™ · © 2026

## Возможности

| Тип | Распознаёт | Действия |
|-----|------------|----------|
| **URL** | `https://...` | Открыть, скопировать домен |
| **JWT** | `eyJ...` | Декодировать header/payload, проверить exp |
| **Base64** | `SGVsbG8=...` | Декодировать в текст |
| **Hex-цвет** | `#ff6b35` / `#abc` | Показать RGB/HSL, скопировать |
| **Координаты** | `55.7558, 37.6176` | Открыть в Organic Maps / OSM |
| **Трек-номер (РФ)** | `RA123456789RU` | Открыть трекинг Почты РФ |
| **Крипто-адреса** | BTC/ETH/SOL/TRX | Открыть в эксплорере |
| **Хеши** | MD5/SHA1/SHA256/SHA512 | Проверить на VirusTotal |
| **Код** | Python/JS/JSON/SQL/Bash/HTML/CSS/YAML/Regex | Копировать, определить язык |
| **Документы РФ** | ИНН, СНИЛС, карта | Валидация (Лун), маскировка |
| **UUID/ULID** | Стандартные форматы | Распознать версию |
| **Email/Телефон** | Стандартные форматы | Копировать |

## Установка

```bash
# Зависимости
pkg install python termux-api
pip install pyjwt

# Клонирование
git clone https://github.com/Xnode-sh/clipd.git ~/clipd
cd ~/clipd
mkdir -p logs
chmod +x clipd.py clipd_tui.py run

# Автозапуск (termux-services)
ln -sf ~/clipd ~/.termux/boot/clipd

# Виджет на рабочий стол
mkdir -p ~/.shortcuts
ln -sf ~/clipd/clipd.py ~/.shortcuts/clipd
```

## Использование

### 1. Виджет / Шорткат (основной способ)
1. Скопируй текст в любом приложении
2. Открой виджет **clipd** на рабочем столе (или Termux:Widget)
3. Появится диалог — вставь текст (или он подхватится из аргументов share sheet)
4. Получишь уведомление с действиями

### 2. Share Sheet (из других приложений)
1. Выдели текст → Поделиться → **clipd**
2. Мгновенный разбор без лишних тапов

### 3. CLI
```bash
# Прямой вызов
python3 ~/clipd/clipd.py "https://github.com/termux/termux-api"

# Из аргументов
termux-share -a send -c "text/plain" "eyJhbGciOiJIUzI1NiJ9..."
```

### 4. TUI — история и поиск
```bash
python3 ~/clipd/clipd_tui.py
```
- `↑↓` — навигация
- `Enter` — скопировать в буфер
- `p` — закрепить/открепить
- `d` — удалить
- `/` — поиск по содержимому
- `t` — фильтр по типу (`url`, `code`, `jwt`, `base64`...)
- `q` — выход

## Структура

```
~/clipd/
├── clipd.py          # Основной скрипт (on-demand)
├── clipd_tui.py      # TUI для истории
├── run               # Сервис для termux-services
├── logs/             # Логи демона
└── clipd.db          # SQLite база (создаётся автоматически, не в git)
```

## Как это работает

1. **Классификация** — regex-патерны по порядку специфичности (трек-номера перед base64, ИНН перед CDEK)
2. **Извлечение мета** — парсинг JWT, декодирование base64, конвертация цветов, геокодинг координат, валидация карт (Лун)
3. **Уведомление** — `termux-notification` с `--action` кнопками, выполняющими shell-команды
4. **Хранилище** — SQLite с полнотекстовым поиском по content, индексами по type/created_at

## Требования

- Termux + Termux:API (апп из F-Droid/Play Market)
- Python 3.10+
- `pyjwt` (`pip install pyjwt`)
- Android 10+ (для уведомлений с действиями)

## Лицензия

MIT — свободное использование с сохранением копирайта.

```
Copyright (c) 2026 Xnode-sh — RED └•TEAM•┐ lab™
```

Полный текст — в файле [LICENSE](LICENSE).
# artfaal.log

Личный блог на Hugo + PaperMod. Деплоится на GitHub Pages, домен `log.artfaal.ru`.

## Стек

- **Hugo** (extended 0.154.0) + тема **PaperMod** (git submodule)
- **GitHub Actions** — автодеплой на push в `master`
- **Python-скрипт** — оптимизация картинок (HEIC/JPEG/PNG -> WebP)
- **Telegram Instant View** — шаблон для красивого просмотра постов

## Как создать новый пост

```bash
# 1. Создать пост
hugo new posts/my-post/index.md

# 2. Подготовить картинки (из папки с исходниками)
python optimize_post_images.py --source "/path/to/photos" --hugo-path content/posts/my-post

# 3. Написать пост, поставить draft: false

# 4. Локальный превью
hugo server -D

# 5. Пуш в master — деплой автоматический
```

## Структура поста

```
content/posts/my-post/
  index.md        # Текст + front matter
  cover.webp      # Обложка
  img_01.webp     # Картинки (нумерация автоматическая)
  img_02.webp
  ...
```

**Front matter:**

```yaml
---
title: "Заголовок"
date: 2026-04-17T12:00:00+03:00
draft: false
tags: ["life", "travel"]
author: "artfaal"
description: "Короткое описание для превью"
cover:
    image: "cover.webp"
    alt: "Обложка поста"
    relative: true
---
```

Картинки в тексте: `![Подпись](img_01.webp)`

## Оптимизация картинок

Скрипт `optimize_post_images.py` делает всю работу:

- Конвертит HEIC/JPEG/PNG/TIFF в WebP (quality 95)
- Ресайзит до 1600px по длинной стороне
- Переименовывает в `img_01.webp`, `img_02.webp`, ...
- Обновляет ссылки в markdown

```bash
# Превью без изменений
python optimize_post_images.py --source "/path" --hugo-path content/posts/my-post --dry-run

# Запуск
python optimize_post_images.py --source "/path" --hugo-path content/posts/my-post
```

Зависимости: `pip install -r requirements.txt` (Pillow + pillow-heif)

## CI/CD

**`.github/workflows/hugo.yml`** — GitHub Actions:

1. Push в `master` или ручной запуск
2. Ставит Hugo 0.154.0 extended
3. `hugo --gc --minify`
4. Деплоит на GitHub Pages

Домен `log.artfaal.ru` привязан через CNAME.

## Telegram Instant View

Шаблон в `instant-view-template.txt` — вставляется в [Instant View Editor](https://instantview.telegram.org/). Настроен на посты блога, автор `artfaal`, кнопка канала `@artfaal_log`.

## Структура проекта

```
hugo.toml                   # Конфиг Hugo
content/posts/              # Посты
layouts/_default/_markup/   # Кастомный рендер картинок (lazy load)
assets/css/extended/        # Кастомные стили (ширина контента, картинки)
themes/PaperMod/            # Тема (submodule, не трогать)
optimize_post_images.py     # Скрипт оптимизации картинок
instant-view-template.txt   # Шаблон Telegram IV
static/CNAME                # Кастомный домен
```

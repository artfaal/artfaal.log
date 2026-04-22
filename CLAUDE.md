# CLAUDE.md

## Правила работы с проектом

### Главный принцип
- **Не создавать дрифт.** Не хардкодить в коде и шаблонах конкретные даты, счётчики постов, списки тегов — они протухнут. Всё, что меняется, должно вычисляться через Hugo (`.Date`, `.GetTerms`, `len .Pages`). Это касается шаблонов, CSS-комментариев, документации.
- **PaperMod — git submodule. Никогда не править `themes/PaperMod/`.** Все изменения — через override в `layouts/` и `assets/css/extended/`. Иначе апдейты темы будут конфликтовать.
- **Единая стилистика с artfaal.ru (terminal-craft).** Палитра, шрифты, язык интерфейса (`// section ::`, `$ date →`, `--section=`) — должны перекликаться. Блог — продолжение сайта, не самостоятельный мирок.

### Архитектура
```
assets/css/extended/*.css   — Hugo конкатенирует все файлы здесь в алфавитном порядке.
                              Префиксы (10-, 20-, ...) управляют каскадом — младшие цифры идут раньше.
layouts/_default/*.html     — override шаблонов страниц (single, list, terms, ...)
layouts/partials/*.html     — override partial'ов (header, footer, post_meta, social_icons, ...)
layouts/partials/extend_head.html   — всегда вызывается PaperMod'ом; сюда Google Fonts, favicon
layouts/partials/extend_footer.html — всегда вызывается; сюда кастомный JS (IntersectionObserver)
themes/PaperMod/            — submodule, ЧИТАТЬ можно, ПИСАТЬ нельзя
```

### Hugo-специфика (уроки)
- **`.Resources.GetMatch` внутри `{{ range }}` — не `$.Resources`.** `$` в range — верхний контекст (у home-page ресурсов нет). Для Page-Bundle cover'ов используй `.Resources.GetMatch .Params.cover.image` на текущем `.`.
- **Thumbnails: `.Fill "WxH Center webp q82"`.** Генерирует optimized thumb из Page-Bundle ресурса, Hugo сам кеширует в `resources/_gen/`. Не отдавай оригинал на 800px — браузер не просчитается.
- **Slug через `path.Base (strings.TrimSuffix "/" .RelPermalink)`.** `.File.ContentBaseName` для Page Bundle даёт `"index"`, а не имя папки.
- **i18n заголовков секций — через `content/{posts,tags}/_index.md` с `title:`**, не через `i18n/ru.yaml`. Заголовок из `_index.md` приоритетнее автозаголовка «Posts/Tags».
- **Dynamic CSS-классы через `data-*`, не через `class="foo-${state}"`.** Скрывает варианты от dead-code-тестов и grep'а.

### CSS-система
- **CSS-переменные в `10-theme.css`, на `:root`.** Не хардкодить цвета/шрифты в других файлах. Палитра отзеркалена на PaperMod-переменные (`--theme`, `--entry`, `--primary`, `--border`, ...) — тема автоматически подхватывает.
- **Mobile-first.** Базовые стили — мобильные, расширяем через `min-width` media queries. Desktop-only эффекты (scanlines) — в `@media (min-width: 700px)`.
- **Нет `!important`** кроме `prefers-reduced-motion` (где без него не обойтись).
- **Transitions — синхронно.** Все hover-свойства одного компонента — одинаковая длительность и easing. Разные durations для разных свойств ломают анимацию визуально.
- **Stagger-reveal через `@keyframes animation`, а не `transition-delay`.** `transition-delay` у родителя протекает на все transitions потомков — hover начинает тормозить. Одноразовый stagger — через `animation + animation-delay`.
- **Экспериментальные блоки — одним `═════════`-разделённым блоком, не вплетать в базовые селекторы.** Легче откатить одним удалением.

### Стиль (terminal-craft)
- **IBM Plex Mono** для display/заголовков (700). **Inter Tight** для body. **JetBrains Mono** для meta/CLI. **Caveat** для handwritten-акцентов.
- **Палитра — dark warm.** `#111110` фон, `#f0ead8` текст, `oklch(0.82 0.17 85)` amber accent, `oklch(0.82 0.14 205)` cyan accent. Не чёрно-белый, не неон.
- **CLI-язык интерфейса.** `// section ::`, `// post ::`, `$ date →`, `$ tags →`, `--section=`. Moustache и emoji — нет. Pattern break (Caveat, polaroid) — редкий, намеренный.
- **CRT-атмосфера — слабее чем на сайте.** Блог = длинный текст, scanlines на 0.18 opacity + mobile отключается. Radial-gradients оставить — они неагрессивные.

### Контент
- **Один пост = одна папка (Page Bundle):** `content/posts/{slug}/index.md` + `cover.webp` + `img_*.webp` рядом.
- **`cover.image` в front matter — относительный путь в Bundle.** `relative: true` обязательно.
- **Заголовки секций** (Posts/Tags) приходят из `content/{posts,tags}/_index.md` — править там, не в шаблонах.
- **Draft-посты** скрыты билдом (`buildDrafts = false`) — не видны даже в списках.

### Изображения
- **Только WebP** в `content/posts/*/*.webp` и `static/`. `.gitignore` блокирует jpg/png/PNG.
- **Pipeline:** `optimize_post_images.py` конвертит сырой материал в WebP и переименовывает (`img_01.webp`, `img_02.webp`, ...). Не править имена вручную.
- **Lazy loading** — на всех `<img>` (`loading="lazy"`). Render-hook `_markup/render-image.html` это делает автоматически для markdown-картинок.
- **Thumbnails — через `.Fill` в шаблоне**, не через CSS `background-image` от оригинала. Hugo кеширует, CDN счастлив.

### Git
- **Deploy: push в `master` → GitHub Actions → GitHub Pages** (`log.artfaal.ru` через CNAME). Workflow в `.github/workflows/hugo.yml` — Hugo версия там закреплена, не двигать без проверки локальной сборкой.
- **НИКОГДА не коммитить без явного разрешения пользователя.** «Разрешение» — слова вроде «коммить», «можно коммитить», «пушим», «ок, коммит». «Отлично», «погнали», «работает» — это про работу, не про коммит.
- **Одна фича — один коммит.** Исключение: большие ребрендинги, где дробление теряет смысл (как `603406b`).
- **Рефакторинг перед коммитом.** Проверить диф, убрать дубликаты правил, мёртвые комментарии.
- **Не пушить force в `master`** — это сломает GitHub Pages деплой.

### Локальная разработка
- **Hugo 0.158.0+extended** (brew). Сверка: `hugo version`.
- **`hugo server --port 1313`** — dev-сервер с livereload. По умолчанию порт 1313.
- **`hugo --gc --minify`** — production-билд в `public/`. Обычно не нужен локально — CI сам.
- **Не коммитить `public/` и `resources/_gen/`** — `.gitignore` это делает.

### Структура
```
hugo.toml                    — конфиг: baseURL, theme, params, menu
content/posts/{slug}/        — Page Bundle каждого поста
content/posts/_index.md      — русский заголовок секции
content/tags/_index.md       — русский заголовок секции
content/search.md            — stub для fuse.js search
assets/css/extended/*.css    — вся кастомная стилистика (каскад по алфавиту)
layouts/_default/*.html      — override шаблонов (single, list, terms)
layouts/partials/*.html      — override partial'ов
layouts/_default/_markup/    — render-hooks для markdown
static/favicon.svg           — amber-circle SVG (та же, что на artfaal.ru)
optimize_post_images.py      — WebP pipeline
themes/PaperMod/             — submodule, read-only
.github/workflows/hugo.yml   — CI → GitHub Pages
CNAME                        — log.artfaal.ru
```

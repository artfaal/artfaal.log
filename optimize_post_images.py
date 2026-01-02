#!/usr/bin/env python3
"""
Скрипт для автоматической оптимизации изображений в постах Hugo блога.

Функции:
- Сжатие JPEG до веб-оптимизированных размеров
- Конвертация HEIC → JPEG
- Конвертация TIFF → PNG (для скриншотов)
- Оптимизация PNG
- Переименование файлов UUID → img_XX
- Синхронизация расширений в markdown
- Валидация и статистика
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    from PIL import Image
    import pillow_heif
except ImportError:
    print("❌ Ошибка: Не установлены необходимые библиотеки.")
    print("Установите зависимости: pip install -r requirements.txt")
    sys.exit(1)

# Регистрируем HEIC формат
pillow_heif.register_heif_opener()


class ImageOptimizer:
    """Класс для оптимизации изображений"""

    def __init__(self, max_width: int = 1600, quality: int = 82, verbose: bool = False):
        self.max_width = max_width
        self.quality = quality
        self.verbose = verbose
        self.stats: List[Dict] = []

    def convert_to_webp(self, input_path: Path, output_path: Path) -> Tuple[int, int]:
        """Конвертирует любое изображение в WebP с высоким качеством"""
        original_size = input_path.stat().st_size

        with Image.open(input_path) as img:
            # Конвертируем в RGB/RGBA
            if img.mode == 'P':
                img = img.convert('RGBA')
            elif img.mode not in ('RGB', 'RGBA'):
                if 'A' in img.mode or img.mode == 'LA':
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')

            # Изменяем размер если нужно (сохраняя пропорции)
            if max(img.width, img.height) > self.max_width:
                if img.width > img.height:
                    new_width = self.max_width
                    new_height = int(img.height * (self.max_width / img.width))
                else:
                    new_height = self.max_width
                    new_width = int(img.width * (self.max_width / img.height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Сохраняем как WebP с высоким качеством
            img.save(
                output_path,
                'WEBP',
                quality=self.quality,
                method=6  # Лучшее сжатие (медленнее, но качественнее)
            )

        new_size = output_path.stat().st_size
        return original_size, new_size

    def process_image(self, input_path: Path, output_path: Path, file_type: str) -> Dict:
        """Обрабатывает одно изображение - конвертирует в WebP"""
        try:
            # Все форматы конвертируем в WebP
            orig_size, new_size = self.convert_to_webp(input_path, output_path)

            # Определяем действие для статистики
            format_map = {
                'jpeg': 'JPEG → WebP',
                'heic': 'HEIC → WebP',
                'tiff': 'TIFF → WebP',
                'png': 'PNG → WebP',
                'webp': 'WebP оптимизирован'
            }
            action = format_map.get(file_type, f'{file_type.upper()} → WebP')

            compression = int((1 - new_size / orig_size) * 100) if orig_size > 0 else 0

            return {
                'success': True,
                'input': input_path.name,
                'output': output_path.name,
                'action': action,
                'original_size': orig_size,
                'new_size': new_size,
                'compression': compression
            }
        except Exception as e:
            return {'success': False, 'input': input_path.name, 'error': str(e)}


def find_markdown_file(source_dir: Path) -> Optional[Path]:
    """Находит markdown файл в директории"""
    # Ищем index.md
    index_md = source_dir / 'index.md'
    if index_md.exists():
        return index_md

    # Ищем любой .md файл
    md_files = list(source_dir.glob('*.md'))
    if md_files:
        return md_files[0]

    return None


def extract_image_references(markdown_content: str) -> List[Tuple[str, str, str]]:
    """
    Извлекает ссылки на изображения из markdown.
    Возвращает список: (полная строка, alt text, путь к файлу)
    """
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(pattern, markdown_content)

    results = []
    for alt, path in matches:
        full_match = f'![{alt}]({path})'
        results.append((full_match, alt, path))

    return results


def get_file_type(filename: str) -> Optional[str]:
    """Определяет тип файла по расширению"""
    ext = Path(filename).suffix.lower()

    if ext in ['.jpg', '.jpeg']:
        return 'jpeg'
    elif ext == '.heic':
        return 'heic'
    elif ext in ['.tif', '.tiff']:
        return 'tiff'
    elif ext == '.png':
        return 'png'
    elif ext == '.webp':
        return 'webp'
    elif ext in ['.mov', '.mp4', '.avi']:
        return 'video'

    return None


def find_file_by_basename(attachments_dir: Path, filename: str) -> Optional[Path]:
    """
    Находит файл по basename (без расширения).
    Это решает проблему когда файлы имеют разные расширения:
    - file.jpeg vs file.jpg
    - file.heic vs file.jpg
    - file.tiff vs file.png
    """
    # Сначала пробуем точное имя
    exact_match = attachments_dir / filename
    if exact_match.exists():
        return exact_match

    # Извлекаем basename (имя без расширения)
    basename = Path(filename).stem

    # Ищем любой файл с этим basename
    for file in attachments_dir.iterdir():
        if file.is_file() and file.stem == basename:
            return file

    # Дополнительная проверка: если файл называется name.ext1.ext2
    # (например, file.jpeg.jpg), пробуем найти его
    for file in attachments_dir.iterdir():
        if file.is_file() and basename in file.name:
            return file

    return None


def format_size(bytes_size: int) -> str:
    """Форматирует размер в читаемый вид"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}TB"


def validate_source_directory(source_dir: Path) -> Tuple[bool, str]:
    """Валидирует исходную директорию"""
    if not source_dir.exists():
        return False, f"Директория не существует: {source_dir}"

    if not source_dir.is_dir():
        return False, f"Это не директория: {source_dir}"

    markdown_file = find_markdown_file(source_dir)
    if not markdown_file:
        return False, f"Не найден markdown файл в {source_dir}"

    attachments_dir = source_dir / 'Attachments'
    if not attachments_dir.exists():
        return False, f"Не найдена папка Attachments в {source_dir}"

    return True, "OK"


def process_post(
    source_dir: Path,
    output_dir: Path,
    hugo_path: Optional[Path],
    max_width: int,
    quality: int,
    dry_run: bool,
    no_rename: bool,
    verbose: bool,
    stats: bool
) -> bool:
    """Основная функция обработки поста"""

    print("🔍 Валидация исходной директории...")
    is_valid, message = validate_source_directory(source_dir)
    if not is_valid:
        print(f"❌ {message}")
        return False
    print(f"✓ {message}")

    # Находим markdown файл
    markdown_file = find_markdown_file(source_dir)
    print(f"📄 Найден markdown: {markdown_file.name}")

    # Читаем markdown
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    # Извлекаем ссылки на изображения
    image_refs = extract_image_references(markdown_content)
    print(f"🖼  Найдено ссылок на изображения: {len(image_refs)}")

    attachments_dir = source_dir / 'Attachments'

    # Собираем список файлов для обработки (в порядке появления в markdown)
    files_to_process: List[Tuple[Path, str, int]] = []  # (путь, новое_имя, индекс)
    processed_files: set = set()
    missing_files: List[str] = []  # Ссылки есть, но файлов нет
    skipped_videos: List[str] = []  # Пропущенные видео
    unknown_types: List[str] = []  # Неизвестные типы файлов

    for idx, (full_match, alt, path) in enumerate(image_refs, start=1):
        # Извлекаем имя файла из пути
        filename = Path(path).name
        if filename.startswith('Attachments/'):
            filename = filename.replace('Attachments/', '')

        # Ищем файл (с поддержкой разных расширений)
        file_path = find_file_by_basename(attachments_dir, filename)

        if not file_path:
            missing_files.append(filename)
            if verbose:
                print(f"⚠️  Файл не найден: {filename}")
            continue

        # Используем реальное имя файла для определения типа
        file_type = get_file_type(file_path.name)
        if file_type == 'video':
            skipped_videos.append(filename)
            if verbose:
                print(f"⏭️  Пропуск видео: {filename}")
            continue

        if file_type is None:
            unknown_types.append(filename)
            if verbose:
                print(f"⚠️  Неизвестный тип файла: {filename}")
            continue

        # Определяем новое имя и расширение
        if no_rename:
            new_name = Path(filename).stem
        else:
            new_name = f"img_{idx:02d}"

        # Все файлы конвертируются в WebP
        new_ext = '.webp'

        files_to_process.append((file_path, new_name + new_ext, idx))
        processed_files.add(file_path.name)  # Используем реальное имя файла

    # Проверяем неиспользуемые файлы
    all_files = set(f.name for f in attachments_dir.iterdir() if f.is_file())
    unused_files = list(all_files - processed_files)

    # Краткая сводка перед обработкой
    if missing_files or unused_files:
        print(f"\n📋 Сводка валидации:")
        if missing_files:
            print(f"   ⚠️  Ссылок без файлов: {len(missing_files)}")
        if unused_files:
            print(f"   ⚠️  Неиспользуемых файлов: {len(unused_files)}")

    if dry_run:
        print("\n" + "=" * 70)
        print("🔍 DRY-RUN РЕЖИМ: Предпросмотр без выполнения")
        print("=" * 70)
        print(f"{'Исходный файл':<35} {'→':<3} {'Новый файл (WebP)':<30}")
        print("─" * 70)
        for file_path, new_name, idx in files_to_process:
            file_type = get_file_type(file_path.name)
            print(f"{file_path.name:<35} → {new_name:<30}")
        print("─" * 70)
        print(f"📊 Всего файлов к обработке: {len(files_to_process)}")
        print(f"📁 Выходная директория: {output_dir}")
        print(f"⚙️  Качество WebP: {quality}")
        print(f"📐 Макс размер: {max_width}px")
        if hugo_path:
            print(f"🚀 Hugo path: {hugo_path}")
        print("=" * 70)
        return True

    # Создаем выходную директорию
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Выходная директория: {output_dir}")

    # Инициализируем оптимизатор
    optimizer = ImageOptimizer(max_width=max_width, quality=quality, verbose=verbose)

    # Обрабатываем изображения
    print("\n🔄 Обработка изображений...\n")
    results: List[Dict] = []
    total_original_size = 0
    total_new_size = 0

    for file_path, new_name, idx in files_to_process:
        file_type = get_file_type(file_path.name)
        output_path = output_dir / new_name

        if verbose:
            print(f"   Обработка: {file_path.name} → {new_name}")

        result = optimizer.process_image(file_path, output_path, file_type)
        results.append(result)

        if result['success']:
            total_original_size += result['original_size']
            total_new_size += result['new_size']
            print(f"✓ {new_name:<20} {format_size(result['original_size']):>8} → {format_size(result['new_size']):>8} ({result['compression']:>2}% сжатие)")
        else:
            print(f"✗ {file_path.name}: {result.get('error', 'Unknown error')}")

    # Обновляем markdown
    print("\n📝 Обновление markdown...")
    new_markdown = markdown_content

    for (full_match, alt, old_path), (file_path, new_name, idx) in zip(image_refs, files_to_process):
        # Определяем новый путь (без Attachments/)
        new_path = new_name

        # Заменяем в markdown
        new_match = f'![{alt}]({new_path})'
        new_markdown = new_markdown.replace(full_match, new_match)

    # Сохраняем обновленный markdown
    output_markdown = output_dir / markdown_file.name
    with open(output_markdown, 'w', encoding='utf-8') as f:
        f.write(new_markdown)
    print(f"✓ Markdown сохранен: {output_markdown.name}")

    # Копируем в Hugo blog если указан путь
    if hugo_path:
        print(f"\n📦 Копирование в Hugo blog: {hugo_path}")
        hugo_path.mkdir(parents=True, exist_ok=True)

        # Копируем markdown
        shutil.copy2(output_markdown, hugo_path / markdown_file.name)

        # Копируем изображения
        for file_path, new_name, idx in files_to_process:
            output_file = output_dir / new_name
            if output_file.exists():
                shutil.copy2(output_file, hugo_path / new_name)

        print(f"✓ Файлы скопированы в {hugo_path}")

    # Статистика
    if stats:
        print("\n" + "=" * 60)
        print("📊 СТАТИСТИКА ОБРАБОТКИ")
        print("=" * 60)
        print(f"Файлов обработано: {len([r for r in results if r['success']])} из {len(results)}")
        if len(results) != len(files_to_process):
            print(f"Пропущено: {len(files_to_process) - len(results)}")
        print(f"\nРазмер до:  {format_size(total_original_size)}")
        print(f"Размер после: {format_size(total_new_size)}")
        if total_original_size > 0:
            savings = total_original_size - total_new_size
            savings_pct = (savings / total_original_size) * 100
            print(f"Экономия: {format_size(savings)} ({savings_pct:.1f}%)")

        # Валидация: отсутствующие файлы
        if missing_files:
            print("\n" + "─" * 60)
            print(f"⚠️  ССЫЛКИ БЕЗ ФАЙЛОВ ({len(missing_files)}):")
            print("Эти изображения упоминаются в markdown, но файлы отсутствуют:")
            for f in missing_files:
                print(f"   • {f}")

        # Валидация: неиспользуемые файлы
        if unused_files:
            print("\n" + "─" * 60)
            print(f"📁 НЕИСПОЛЬЗУЕМЫЕ ФАЙЛЫ ({len(unused_files)}):")
            print("Эти файлы есть в Attachments/, но не используются в markdown:")
            for f in sorted(unused_files):
                file_path = attachments_dir / f
                size = format_size(file_path.stat().st_size)
                print(f"   • {f:<40} ({size})")

        # Пропущенные видео
        if skipped_videos:
            print("\n" + "─" * 60)
            print(f"⏭️  ПРОПУЩЕННЫЕ ВИДЕО ({len(skipped_videos)}):")
            for f in skipped_videos:
                print(f"   • {f}")

        print("=" * 60)

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Оптимизация изображений для Hugo блога',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:

  # Предпросмотр (dry-run)
  python optimize_post_images.py --source "Поездка Дубай 2025" --dry-run

  # Обработка с сохранением в processed/
  python optimize_post_images.py --source "Поездка Дубай 2025"

  # Обработка и копирование в Hugo blog
  python optimize_post_images.py --source "Поездка Дубай 2025" \\
    --hugo-path "content/posts/dubai-2025"
        '''
    )

    parser.add_argument(
        '--source',
        type=str,
        required=True,
        help='Путь к директории с постом (должна содержать markdown и Attachments/)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Путь для обработанных файлов (по умолчанию: source/processed)'
    )
    parser.add_argument(
        '--hugo-path',
        type=str,
        help='Путь к Hugo blog posts для автокопирования'
    )
    parser.add_argument(
        '--max-width',
        type=int,
        default=1600,
        help='Максимальный размер (длинная сторона) для WebP (по умолчанию: 1600)'
    )
    parser.add_argument(
        '--quality',
        type=int,
        default=95,
        help='Качество WebP 1-100 (по умолчанию: 95 - около максимального)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Предпросмотр без выполнения'
    )
    parser.add_argument(
        '--no-rename',
        action='store_true',
        help='Не переименовывать файлы в img_XX'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод'
    )
    parser.add_argument(
        '--no-stats',
        action='store_true',
        help='Не показывать статистику'
    )

    args = parser.parse_args()

    # Конвертируем пути
    source_dir = Path(args.source).expanduser().resolve()

    if args.output:
        output_dir = Path(args.output).expanduser().resolve()
    else:
        output_dir = source_dir / 'processed'

    hugo_path = None
    if args.hugo_path:
        hugo_path = Path(args.hugo_path).expanduser().resolve()

    # Запускаем обработку
    print("🚀 Оптимизация изображений для Hugo блога\n")
    success = process_post(
        source_dir=source_dir,
        output_dir=output_dir,
        hugo_path=hugo_path,
        max_width=args.max_width,
        quality=args.quality,
        dry_run=args.dry_run,
        no_rename=args.no_rename,
        verbose=args.verbose,
        stats=not args.no_stats
    )

    if success:
        print("\n✅ Готово!")
    else:
        print("\n❌ Ошибка при обработке")
        sys.exit(1)


if __name__ == '__main__':
    main()

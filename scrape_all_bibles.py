import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from bible_scraper import CHAPTER_COUNT, fetch_chapter
from book_maps import NORWEGIAN, ENGLISH
from scrape_entire_bible import BOOK_ORDER

TRANSLATIONS = [
    {"id": 102,  "name": "NB88",       "lang": NORWEGIAN},
    {"id": 2216, "name": "BGO",         "lang": NORWEGIAN},
    {"id": 29,   "name": "Bibel2011",   "lang": NORWEGIAN},
    {"id": 121,  "name": "Bibel1930",   "lang": NORWEGIAN},
    {"id": 100,  "name": "NASB1995",    "lang": ENGLISH},
    {"id": 59,   "name": "ESV",         "lang": ENGLISH},
    {"id": 114,  "name": "NKJV",        "lang": ENGLISH},
    {"id": 111,  "name": "NIV",         "lang": ENGLISH},
    {"id": 1,    "name": "KJV",         "lang": ENGLISH},
]

RATE_LIMIT = 0.1
MAX_WORKERS = 4

_print_lock = threading.Lock()


def safe_print(*args, **kwargs):
    with _print_lock:
        print(*args, **kwargs)


def _present_chapters(verses: dict) -> set:
    """Returns the set of chapter numbers present in a verses dict."""
    chapters = set()
    for key in verses:
        if key == "headings":
            continue
        parts = key.split(".")
        if len(parts) >= 3:
            chapters.add(int(parts[1]))
    return chapters


def scrape_book_task(translation_id: int, name: str, lang: dict, book: str):
    idx = BOOK_ORDER.index(book) + 1
    book_name = lang.get(book, book)
    filename = f"{idx:02d}_{book}_{book_name}.json"
    output_dir = f"bible_{translation_id}_{name}"
    filepath = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)

    expected = set(range(1, CHAPTER_COUNT[book] + 1))
    existing_verses = {}

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing_verses = json.load(f)
        missing = expected - _present_chapters(existing_verses)
        if not missing:
            return "skipped", filepath
    else:
        missing = expected

    verses = {k: v for k, v in existing_verses.items() if k != "headings"}
    headings = dict(existing_verses.get("headings", {}))

    try:
        for i, chapter in enumerate(sorted(missing)):
            chapter_result = fetch_chapter(book, chapter, translation_id, include_headings=True)
            headings.update(chapter_result.pop("headings", {}))
            verses.update(chapter_result)
            if i < len(missing) - 1:
                time.sleep(RATE_LIMIT)
    except Exception as e:
        return "error", f"[{name}] {book}: {e}"

    if headings:
        verses["headings"] = headings

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    verse_count = sum(1 for k in verses if k != "headings")
    heading_count = len(verses.get("headings", {}))
    was_partial = bool(existing_verses)
    return "done", (name, book_name, book, verse_count, heading_count, len(missing), was_partial)


if __name__ == "__main__":
    tasks = [
        (t["id"], t["name"], t["lang"], book)
        for t in TRANSLATIONS
        for book in BOOK_ORDER
    ]
    total = len(tasks)
    completed = 0

    print(f"Scraping {len(TRANSLATIONS)} translations × {len(BOOK_ORDER)} books = {total} tasks ({MAX_WORKERS} workers)\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_book_task, *task): task for task in tasks}

        for future in as_completed(futures):
            completed += 1

            try:
                status, payload = future.result()
            except Exception as e:
                safe_print(f"  [ERROR] {e}", file=sys.stderr)
                continue

            if status == "done":
                name, book_name, book, verse_count, heading_count, fetched_chapters, was_partial = payload
                tag = f"filled {fetched_chapters} ch" if was_partial else f"{fetched_chapters} ch"
                safe_print(f"  [{completed}/{total}] {name} {book_name} ({book}) -> {verse_count} verses, {heading_count} headings ({tag})")
            elif status == "error":
                safe_print(f"  [ERROR] {payload}", file=sys.stderr)

    print("\nDone!")

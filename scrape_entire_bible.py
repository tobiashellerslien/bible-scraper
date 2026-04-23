import argparse
import json
import os
import sys
import time

from bible_scraper import CHAPTER_COUNT, fetch_book
from book_maps import NORWEGIAN, ENGLISH

DEFAULT_TRANSLATION_ID = 102
DEFAULT_LANG = "norwegian"
LANG_MAP = {"norwegian": NORWEGIAN, "english": ENGLISH}

BOOK_ORDER = [
    "GEN", "EXO", "LEV", "NUM", "DEU",
    "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR",
    "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SNG", "ISA", "JER", "LAM",
    "EZK", "DAN", "HOS", "JOL", "AMO",
    "OBA", "JON", "MIC", "NAM", "HAB",
    "ZEP", "HAG", "ZEC", "MAL",
    "MAT", "MRK", "LUK", "JHN", "ACT",
    "ROM", "1CO", "2CO", "GAL", "EPH",
    "PHP", "COL", "1TH", "2TH", "1TI",
    "2TI", "TIT", "PHM", "HEB", "JAS",
    "1PE", "2PE", "1JN", "2JN", "3JN",
    "JUD", "REV",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--translation-id", type=int, default=DEFAULT_TRANSLATION_ID)
    parser.add_argument("--lang", choices=LANG_MAP.keys(), default=DEFAULT_LANG)
    parser.add_argument("--include-headings", action="store_true", default=False)
    parser.add_argument("--include-footnotes", action="store_true", default=False)
    parser.add_argument("--rate-limit", type=float, default=0.1, metavar="SECONDS")
    args = parser.parse_args()

    translation_id = args.translation_id
    lang = LANG_MAP[args.lang]
    include_headings = args.include_headings
    include_footnotes = args.include_footnotes
    output_dir = f"bible_{translation_id}"

    os.makedirs(output_dir, exist_ok=True)
    existing = set(os.listdir(output_dir))

    for book in BOOK_ORDER:
        idx = BOOK_ORDER.index(book) + 1
        name = lang.get(book, book)
        filename = f"{idx:02d}_{book}_{name}.json"

        if filename in existing:
            print(f"skipped {filename}, already exists")
            continue

        print(f"[fetching]  {name} ({book}, {CHAPTER_COUNT[book]} chapters) ...")

        try:
            verses = fetch_book(book, translation_id, include_headings=include_headings, include_footnotes=include_footnotes, rate_limit=args.rate_limit)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            print("  Waiting 5 seconds and continuing with the next book ...")
            time.sleep(5)
            continue

        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(verses, f, ensure_ascii=False, indent=2)

        print(f"  Saved {len(verses)} verses -> {filepath}")

    print("\nDone!")


if __name__ == "__main__":
    main()

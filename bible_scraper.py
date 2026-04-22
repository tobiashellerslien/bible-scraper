import requests
import json
import re
import time
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_URL = "https://www.bible.com/bible"
RATE_LIMIT = 0.1  # seconds between requests in fetch_book

CHAPTER_COUNT = {
    # Old Testament
    "GEN": 50, "EXO": 40, "LEV": 27, "NUM": 36, "DEU": 34,
    "JOS": 24, "JDG": 21, "RUT":  4, "1SA": 31, "2SA": 24,
    "1KI": 22, "2KI": 25, "1CH": 29, "2CH": 36, "EZR": 10,
    "NEH": 13, "EST":  10, "JOB": 42, "PSA": 150, "PRO": 31,
    "ECC": 12, "SNG":  8, "ISA": 66, "JER": 52, "LAM":  5,
    "EZK": 48, "DAN": 12, "HOS": 14, "JOL":  3, "AMO":  9,
    "OBA":  1, "JON":  4, "MIC":  7, "NAM":  3, "HAB":  3,
    "ZEP":  3, "HAG":  2, "ZEC": 14, "MAL":  4,
    # New Testament
    "MAT": 28, "MRK": 16, "LUK": 24, "JHN": 21, "ACT": 28,
    "ROM": 16, "1CO": 16, "2CO": 13, "GAL":  6, "EPH":  6,
    "PHP":  4, "COL":  4, "1TH":  5, "2TH":  3, "1TI":  6,
    "2TI":  4, "TIT":  3, "PHM":  1, "HEB": 13, "JAS":  5,
    "1PE":  5, "2PE":  3, "1JN":  5, "2JN":  1, "3JN":  1,
    "JUD":  1, "REV": 22,
}


_HEADING_CLASSES = {"s", "s1", "s2", "s3"}


def fetch_chapter(book: str, chapter: int, translation_id: int, include_headings: bool = False) -> dict:
    """
    Fetches all verses in a chapter from bible.com.

    Returns a dict: { "GEN.1.1": "text", "GEN.1.2": "text", ... }
    Psalms with an introduction get the intro stored as verse 0.

    When include_headings=True, a "headings" key is added to the result dict mapping
    each heading to the USFM of the first verse that follows it, e.g.:
    { "GEN.6.1": "Menneskenes ondskap", "GEN.6.8": "Noah" }

    book:             USFM abbreviation, e.g. "GEN", "PSA", "JHN"
    chapter:          chapter number (int)
    translation_id:   bible.com translation ID, e.g. 102 (NB88). Found in the URL when viewing a chapter on bible.com, e.g. https://www.bible.com/bible/102/GEN.1
    include_headings: if True, section headings are included in the returned dict under the "headings" key
    """
    url = f"{BASE_URL}/{translation_id}/{book}.{chapter}"

    try:
        page = requests.get(url, headers=HEADERS, timeout=10)
        page.raise_for_status()
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to fetch {book}.{chapter}: {e}")

    soup = BeautifulSoup(page.text, "html.parser")
    script_tag = soup.find("script", {"id": "__NEXT_DATA__"})

    data = json.loads(script_tag.get_text())
    html_content = data["props"]["pageProps"]["chapterInfo"]["content"]

    inner_soup = BeautifulSoup(html_content, "html.parser")

    result = {}

    # Handle psalm introductions in some translations, stored as verse 0
    intro_div = inner_soup.find("div", class_="d")
    if intro_div:
        content_spans = intro_div.find_all("span", class_="content")
        intro_text = "".join(span.get_text() for span in content_spans)
        intro_text = re.sub(r"\s+", " ", intro_text).strip()
        if intro_text:
            result[f"{book}.{chapter}.0"] = intro_text

    # Handle regular verses
    for verse in inner_soup.find_all("span", class_="verse"):
        usfm = verse.get("data-usfm")
        content_spans = verse.find_all("span", class_="content")
        text = "".join(span.get_text() for span in content_spans)
        text = re.sub(r"\s+", " ", text).strip()

        if usfm in result:
            result[usfm] = re.sub(r"\s+", " ", result[usfm] + " " + text).strip()
        else:
            result[usfm] = text

    if include_headings:
        chapter_div = inner_soup.find("div", class_=lambda c: c and "chapter" in c)
        if chapter_div:
            headings = {}
            pending = []
            seen = set()
            for el in chapter_div.descendants:
                if not hasattr(el, "get"):
                    continue
                cls = set(el.get("class") or [])
                if cls & _HEADING_CLASSES and el.name == "div":
                    hspan = el.find("span", class_="heading")
                    if hspan:
                        pending.append(hspan.get_text().strip())
                elif "verse" in cls and el.name == "span":
                    usfm = el.get("data-usfm", "")
                    if usfm and usfm not in seen:
                        seen.add(usfm)
                        if pending:
                            headings[usfm] = " / ".join(pending)
                            pending = []
            if headings:
                result["headings"] = headings

    return result


def fetch_verse(book: str, chapter: int, verse: int, translation_id: int) -> dict:
    """Fetches a single verse. Returns a dict: { "JHN.3.16": "text" }"""
    scraped_chapter = fetch_chapter(book, chapter, translation_id)
    usfm = f"{book}.{chapter}.{verse}"

    if usfm not in scraped_chapter:
        raise KeyError(f"Verse {usfm} not found in chapter, check that the verse number is correct")

    return {usfm: scraped_chapter[usfm]}


def fetch_verse_range(book: str, chapter: int, verse_start: int, verse_end: int, translation_id: int) -> dict:
    """Fetches a span of verses from the same chapter. Returns a dict: { "GEN.1.1": "text", ... }"""
    scraped_chapter = fetch_chapter(book, chapter, translation_id)

    result = {}
    for verse in range(verse_start, verse_end + 1):
        usfm = f"{book}.{chapter}.{verse}"
        if usfm not in scraped_chapter:
            raise KeyError(f"Verse {usfm} not found in chapter, check that the verse number is correct")
        result[usfm] = scraped_chapter[usfm]

    return result


def fetch_verse_range_cross_chapter(book: str, chapter_start: int, verse_start: int, chapter_end: int, verse_end: int, translation_id: int, rate_limit: float = RATE_LIMIT) -> dict:
    """
    Fetches a span of verses across multiple chapters.

    Returns a dict: { "ISA.52.13": "text", ..., "ISA.53.12": "text" }

    book:           USFM abbreviation
    chapter_start:  first chapter number
    verse_start:    first verse in the first chapter
    chapter_end:    last chapter number
    verse_end:      last verse in the last chapter
    translation_id: bible.com translation ID
    rate_limit:     seconds to sleep between chapter requests (default: RATE_LIMIT)
    """
    if chapter_start == chapter_end:
        return fetch_verse_range(book, chapter_start, verse_start, verse_end, translation_id)

    result = {}

    for chapter in range(chapter_start, chapter_end + 1):
        scraped_chapter = fetch_chapter(book, chapter, translation_id)

        for usfm, text in scraped_chapter.items():
            _, ch, v = usfm.split(".")
            ch, v = int(ch), int(v)

            if chapter == chapter_start and v < verse_start:
                continue
            if chapter == chapter_end and v > verse_end:
                continue

            result[usfm] = text

        if chapter < chapter_end:
            time.sleep(rate_limit)

    return result


def fetch_book(book: str, translation_id: int, include_headings: bool = False, rate_limit: float = RATE_LIMIT) -> dict:
    """
    Fetches all verses in a book. Returns a dict: { "GEN.1.1": "text", ... }

    When include_headings=True, a "headings" key is included in the result with all
    section headings across the book, keyed by the USFM of the verse each heading precedes.

    rate_limit: seconds to sleep between chapter requests (default: RATE_LIMIT)
    """
    if book not in CHAPTER_COUNT:
        raise KeyError(f"Unknown book: '{book}', use a USFM abbreviation, e.g. 'GEN', 'PSA'")

    result = {}
    all_headings = {}
    total = CHAPTER_COUNT[book]

    for chapter in range(1, total + 1):
        chapter_result = fetch_chapter(book, chapter, translation_id, include_headings=include_headings)
        if include_headings:
            all_headings.update(chapter_result.pop("headings", {}))
        result.update(chapter_result)
        print(f"  Fetched {book} chapter {chapter}/{total}")
        if chapter < total:
            time.sleep(rate_limit)

    if include_headings and all_headings:
        result["headings"] = all_headings

    return result


def decode_usfm(usfm: str, book_names: dict = None) -> tuple:
    """
    Decodes a USFM string into book, chapter, and verse.

    usfm:       e.g. "GEN.1.1" or "PSA.23.0"
    book_names: optional dict with custom book names, e.g. {"GEN": "1. Mosebok", "PSA": "Salmenes bok"}
                If not provided, the USFM abbreviation is returned as the book name.

    Returns a tuple: (book name, chapter, verse)
    """
    parts = usfm.split(".")
    book_abbr = parts[0]
    chapter = int(parts[1])
    verse = int(parts[2])

    book = book_names.get(book_abbr, book_abbr) if book_names else book_abbr

    return book, chapter, verse


if __name__ == "__main__":
    # Usage examples:

    print("Fetching Psalm 23 in Bibel2011...")
    chapter = fetch_chapter("PSA", 23, 29)
    for usfm, text in chapter.items():
        print(f"{usfm}: {text}")

    print("\nFetching John 3:16 in NB88...")
    verse = fetch_verse("JHN", 3, 16, 102)
    for usfm, text in verse.items():
        print(f"{usfm}: {text}")

    print("\nFetching Genesis 1:1-6 in NASB1995...")
    verse_range = fetch_verse_range("GEN", 1, 1, 6, 100)
    for usfm, text in verse_range.items():
        print(f"{usfm}: {text}")

    print("\nFetching Isaiah 52:13-53:12 in NB88...")
    cross = fetch_verse_range_cross_chapter("ISA", 52, 13, 53, 12, 102)
    for usfm, text in cross.items():
        print(f"{usfm}: {text}")

    print("\nFetching all of Jonah in NB88...")
    book = fetch_book("JON", 102)
    for usfm, text in book.items():
        print(f"{usfm}: {text}")

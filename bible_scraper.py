import requests
import json
import re
import time
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_URL = "https://www.bible.com/bible"
RATE_LIMIT = 0.5  # sekunder mellom requests i fetch_book

CHAPTER_COUNT = {
    # Det gamle testamentet
    "GEN": 50, "EXO": 40, "LEV": 27, "NUM": 36, "DEU": 34,
    "JOS": 24, "JDG": 21, "RUT":  4, "1SA": 31, "2SA": 24,
    "1KI": 22, "2KI": 25, "1CH": 29, "2CH": 36, "EZR": 10,
    "NEH": 13, "EST":  10, "JOB": 42, "PSA": 150, "PRO": 31,
    "ECC": 12, "SNG":  8, "ISA": 66, "JER": 52, "LAM":  5,
    "EZK": 48, "DAN": 12, "HOS": 14, "JOL":  3, "AMO":  9,
    "OBA":  1, "JON":  4, "MIC":  7, "NAH":  3, "HAB":  3,
    "ZEP":  3, "HAG":  2, "ZEC": 14, "MAL":  4,
    # Det nye testamentet
    "MAT": 28, "MRK": 16, "LUK": 24, "JHN": 21, "ACT": 28,
    "ROM": 16, "1CO": 16, "2CO": 13, "GAL":  6, "EPH":  6,
    "PHP":  4, "COL":  4, "1TH":  5, "2TH":  3, "1TI":  6,
    "2TI":  4, "TIT":  3, "PHM":  1, "HEB": 13, "JAS":  5,
    "1PE":  5, "2PE":  3, "1JN":  5, "2JN":  1, "3JN":  1,
    "JUD":  1, "REV": 22,
}


def fetch_chapter(book: str, chapter: int, translation_id: int) -> dict:
    """
    Henter alle vers i et kapittel fra bible.com.

    Returnerer en dict: { "GEN.1.1": "tekst", "GEN.1.2": "tekst", ... }
    Salmer med intro får introen som vers 0.

    book:           USFM-forkortelse, f.eks. "GEN", "PSA", "JHN"
    chapter:        kapittelnummer (int)
    translation_id: bible.com oversettelse-ID, f.eks. 102 (NB88). Finnes i URL-en når du ser på et kapittel på bible.com, f.eks. https://www.bible.com/bible/102/GEN.1
    """
    url = f"{BASE_URL}/{translation_id}/{book}.{chapter}"

    try:
        page = requests.get(url, headers=HEADERS, timeout=10)
        page.raise_for_status()
    except requests.RequestException as e:
        raise ConnectionError(f"Kunne ikke hente {book}.{chapter}: {e}")

    soup = BeautifulSoup(page.text, "html.parser")
    script_tag = soup.find("script", {"id": "__NEXT_DATA__"})

    data = json.loads(script_tag.get_text())
    html_content = data["props"]["pageProps"]["chapterInfo"]["content"]

    inner_soup = BeautifulSoup(html_content, "html.parser")

    result = {}

    # Håndterer introen for salmer i noen oversettelser, lagrer som vers 0
    intro_div = inner_soup.find("div", class_="d")
    if intro_div:
        content_spans = intro_div.find_all("span", class_="content")
        intro_text = "".join(span.get_text() for span in content_spans)
        intro_text = re.sub(r"\s+", " ", intro_text).strip()
        if intro_text:
            result[f"{book}.{chapter}.0"] = intro_text

    # Håndterer vanlige vers
    for verse in inner_soup.find_all("span", class_="verse"):
        usfm = verse.get("data-usfm")
        content_spans = verse.find_all("span", class_="content")
        text = "".join(span.get_text() for span in content_spans)
        text = re.sub(r"\s+", " ", text).strip()
        text = text.replace("*", "")

        if usfm in result:
            result[usfm] = re.sub(r"\s+", " ", result[usfm] + " " + text).strip()
        else:
            result[usfm] = text

    return result


def fetch_verse(book: str, chapter: int, verse: int, translation_id: int) -> dict:
    """Henter ett enkelt vers. Returnerer en dict: { "JHN.3.16": "tekst" }"""
    scraped_chapter = fetch_chapter(book, chapter, translation_id)
    usfm = f"{book}.{chapter}.{verse}"

    if usfm not in scraped_chapter:
        raise KeyError(f"Vers {usfm} finnes ikke i kapitlet, sjekk at versnummeret er riktig")

    return {usfm: scraped_chapter[usfm]}


def fetch_verse_range(book: str, chapter: int, verse_start: int, verse_end: int, translation_id: int) -> dict:
    """Henter et intervall av vers fra samme kapittel. Returnerer en dict: { "GEN.1.1": "tekst", ... }"""
    scraped_chapter = fetch_chapter(book, chapter, translation_id)

    result = {}
    for verse in range(verse_start, verse_end + 1):
        usfm = f"{book}.{chapter}.{verse}"
        if usfm not in scraped_chapter:
            raise KeyError(f"Vers {usfm} finnes ikke i kapitlet, sjekk at versnummeret er riktig")
        result[usfm] = scraped_chapter[usfm]

    return result


def fetch_verse_range_cross_chapter(book: str, chapter_start: int, verse_start: int, chapter_end: int, verse_end: int, translation_id: int) -> dict:
    """
    Henter et intervall av vers som går over flere kapitler.

    Returnerer en dict: { "ISA.52.13": "tekst", ..., "ISA.53.12": "tekst" }

    book:           USFM-forkortelse
    chapter_start:  første kapittels nummer
    verse_start:    første vers i første kapittel
    chapter_end:    siste kapittels nummer
    verse_end:      siste vers i siste kapittel
    translation_id: bible.com oversettelse-ID
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
            time.sleep(RATE_LIMIT)

    return result


def fetch_book(book: str, translation_id: int) -> dict:
    """Henter alle vers i en bok. Returnerer en dict: { "GEN.1.1": "tekst", ... }"""
    if book not in CHAPTER_COUNT:
        raise KeyError(f"Ukjent bok: '{book}', bruk USFM-forkortelse, f.eks. 'GEN', 'PSA'")

    result = {}
    total = CHAPTER_COUNT[book]

    for chapter in range(1, total + 1):
        result.update(fetch_chapter(book, chapter, translation_id))
        if chapter < total:
            time.sleep(RATE_LIMIT)

    return result


def decode_usfm(usfm: str, book_names: dict = None) -> tuple:
    """
    Dekoder en USFM-streng til bok, kapittel og vers.

    usfm:       f.eks. "GEN.1.1" eller "PSA.23.0"
    book_names: valgfri dict med egne boknavn, f.eks. {"GEN": "1. Mosebok", "PSA": "Salmenes bok"}
                Hvis ikke oppgitt returneres USFM-forkortelsen som boknavn.

    Returnerer en tuple: (boknavn, kapittel, vers)
    """
    parts = usfm.split(".")
    book_abbr = parts[0]
    chapter = int(parts[1])
    verse = int(parts[2])

    book = book_names.get(book_abbr, book_abbr) if book_names else book_abbr

    return book, chapter, verse


if __name__ == "__main__":
    # Eksempler på bruk:¨
    
    print("Henter Salme 23 i Bibel2011...")
    chapter = fetch_chapter("PSA", 23, 29)
    for usfm, text in chapter.items():
        print(f"{usfm}: {text}")

    print("\nHenter Johannes 3:16 i NB88...")
    verse = fetch_verse("JHN", 3, 16, 102)
    for usfm, text in verse.items():
        print(f"{usfm}: {text}")

    print("\nHenter 1. Mosebok 1:1-6 i NASB1995...")
    verse_range = fetch_verse_range("GEN", 1, 1, 6, 100)
    for usfm, text in verse_range.items():
        print(f"{usfm}: {text}")

    print("\nHenter Jesaja 52:13-53:12 i NB88...")
    cross = fetch_verse_range_cross_chapter("ISA", 52, 13, 53, 12, 102)
    for usfm, text in cross.items():
        print(f"{usfm}: {text}")

    print("\nHenter hele Jona i NB88...")
    book = fetch_book("JON", 102)
    for usfm, text in book.items():
        print(f"{usfm}: {text}")

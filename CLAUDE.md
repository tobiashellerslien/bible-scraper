# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A Python scraper module for [bible.com](https://www.bible.com) that fetches Bible verse text by book, chapter, or verse range.

## Running

```bash
.venv/Scripts/python.exe -m pip install requests beautifulsoup4
.venv/Scripts/python.exe bible-scraper.py
```

Translation IDs are found in the URL on bible.com, e.g. `https://www.bible.com/bible/102/GEN.1` → ID is `102` (Norwegian NB88/07), `111` = NIV.

## Module API (`bible-scraper.py`)

All fetch functions return a `dict` with USFM keys and verse text as values, e.g. `{"GEN.1.1": "I begynnelsen..."}`.

| Function | Description |
|----------|-------------|
| `fetch_chapter(book, chapter, translation_id)` | All verses in one chapter |
| `fetch_verse(book, chapter, verse, translation_id)` | Single verse |
| `fetch_verse_range(book, chapter, verse_start, verse_end, translation_id)` | Verse range within one chapter |
| `fetch_verse_range_cross_chapter(book, chapter_start, verse_start, chapter_end, verse_end, translation_id)` | Verse range spanning chapter boundaries |
| `fetch_book(book, translation_id)` | All verses in a book |
| `decode_usfm(usfm, book_names=None)` | Decodes `"GEN.1.1"` → `("GEN", 1, 1)`, or with a book name map → `("1. Mosebok", 1, 1)` |

`book_maps.py` contains `NORWEGIAN` and `ENGLISH` dicts mapping USFM abbreviations to book names, for use with `decode_usfm`.

## Architecture

The scraper fetches chapters from bible.com's JSON chapter API (`https://nodejs.bible.com/api/bible/chapter/3.1?id=<translation_id>&reference=<BOOK>.<chapter>`, see `API_URL` in `bible_scraper.py`). The `content` field of that JSON is pre-rendered chapter HTML, which is parsed with BeautifulSoup to extract `span.verse` elements by their `data-usfm` attribute.

The API is used instead of the regular `https://www.bible.com/bible/...` HTML pages because those now return an anti-bot JS challenge (an F5/Fastly "Client Challenge" stub with no content) for most translations. The API returns the same chapter HTML the page's `__NEXT_DATA__` blob used to expose, but as plain JSON, with no challenge.

Key parsing details:
- Some translations split a verse across multiple `span.verse` elements (e.g. poetry); text is accumulated per USFM key
- `span.note` cross-references are excluded by only reading `span.content` children
- Whitespace is normalized with `re.sub(r"\s+", " ", ...)` to handle tabs/newlines from poetic indentation
- `*` footnote markers are stripped
- Psalm introductions appear in `<div class="d">` outside any verse span and are stored as verse `0` (e.g. `PSA.23.0`)
- `fetch_book` and `fetch_verse_range_cross_chapter` sleep `RATE_LIMIT` seconds (default 0.4) between chapter requests

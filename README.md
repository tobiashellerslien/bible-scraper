# Bible Scraper

A Python module for scraping Bible verse text from [bible.com](https://www.bible.com). Fetch single verses, verse ranges, chapters, or entire books. Returns plain Python dicts so you can pipe the data wherever you need it.

## Setup

```bash
pip install requests beautifulsoup4
```

## Module usage

All functions are in `bible_scraper.py` and use USFM book abbreviations (e.g. `"GEN"`, `"PSA"`, `"JHN"`). Translation IDs are found in the bible.com URL, e.g. `https://www.bible.com/bible/102/GEN.1` -> ID is `102`.

All fetch functions return a `dict` with USFM keys and verse text as values:

```python
from bible_scraper import fetch_verse, fetch_verse_range, fetch_chapter, fetch_book, fetch_verse_range_cross_chapter, decode_usfm
from book_maps import NORWEGIAN, ENGLISH

# Single verse
fetch_verse("JHN", 3, 16, 102)
# -> {"JHN.3.16": "For så høyt har Gud elsket verden..."}

# Verse range within one chapter
fetch_verse_range("GEN", 1, 1, 5, 102)

# Verse range across chapter boundaries
fetch_verse_range_cross_chapter("ISA", 52, 13, 53, 12, 102)

# Whole chapter
fetch_chapter("PSA", 23, 111)

# Whole book
fetch_book("JON", 102)

# Decode a USFM key to its parts
decode_usfm("JHN.3.16", NORWEGIAN)
# -> ("Johannes", 3, 16)
```

`book_maps.py` contains `NORWEGIAN` and `ENGLISH` dicts for use with `decode_usfm`.

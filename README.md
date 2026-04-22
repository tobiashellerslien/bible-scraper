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
# -> {"JHN.3.16": "For så har Gud elsket verden..."}

# Verse range within one chapter
fetch_verse_range("GEN", 1, 1, 5, 102)

# Verse range across chapter boundaries
fetch_verse_range_cross_chapter("ISA", 52, 13, 53, 12, 102)

# Whole chapter — optionally include section headings
fetch_chapter("PSA", 23, 102)
fetch_chapter("GEN", 6, 102, include_headings=True)
# -> {"GEN.6.1": "Da nå menneskene...", ...,
#     "headings": {"GEN.6.1": "Menneskenes ondskap", "GEN.6.9": "Noah", ...}}

# Whole book — also supports include_headings and rate_limit
fetch_book("JON", 102)
fetch_book("JON", 102, include_headings=True, rate_limit=0.5)

# Decode a USFM key to its parts
decode_usfm("JHN.3.16", NORWEGIAN)
# -> ("Johannes", 3, 16)
```

`book_maps.py` contains `NORWEGIAN` and `ENGLISH` dicts for use with `decode_usfm`.

### Section headings

`fetch_chapter` and `fetch_book` accept `include_headings=True`. When set, a `"headings"` key is added to the returned dict mapping each heading to the USFM of the first verse it precedes:

```python
{"GEN.6.1": "Menneskenes ondskap", "GEN.6.9": "Noah", ...}
```

`fetch_verse`, `fetch_verse_range`, and `fetch_verse_range_cross_chapter` never include headings.

## Scraping an entire Bible

`scrape_entire_bible.py` fetches every book and saves each as a JSON file in an output directory.

```bash
python scrape_entire_bible.py # defaults: translation 102, Norwegian filenames
python scrape_entire_bible.py --translation-id 100 --lang english --include-headings --rate-limit 0.5
```

| Flag | Default | Description |
|------|---------|-------------|
| `--translation-id` | `102` | bible.com translation ID |
| `--lang` | `norwegian` | Book name language (`norwegian` or `english`), used only in filenames |
| `--include-headings` | off | Include section headings in JSON output |
| `--rate-limit` | `0.1` | Seconds to sleep between chapter requests |

Output is written to `bible_<translation-id>/`, one file per book named `01_GEN_Genesis.json` etc. Already-completed books are skipped on reruns.

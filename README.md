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

# Whole book
fetch_book("JON", 102, include_headings=True, rate_limit=0.5)

# Decode a USFM key to its parts
decode_usfm("JHN.3.16", NORWEGIAN)
# -> ("Johannes", 3, 16)
```

`book_maps.py` contains `NORWEGIAN` and `ENGLISH` dicts for use with `decode_usfm`.

### Section headings

`fetch_chapter` and `fetch_book` accept `include_headings=True`. When set, a `"headings"` key is added to the returned dict mapping each heading to the USFM of the verse it precedes:

```python
{"GEN.6.1": "Menneskenes ondskap", "GEN.6.9": "Noah", ...}
```

Multiple heading types are captured: section headings (`s`, `s1`–`s3`), major section headings (`ms`), psalm acrostic letters (`qa`, e.g. "Aleph"), and major reference ranges (`mr`, e.g. "Psalms 1–41"). Multiple headings between the same pair of verses are joined with ` / `.

Psalm introductions (e.g. "A Psalm of David") are stored as verse `0` (e.g. `PSA.23.0`). If a heading precedes the introduction, it is associated with verse `0`.

`fetch_verse`, `fetch_verse_range`, and `fetch_verse_range_cross_chapter` never include headings.

### Notes on data

- Some translations merge two verses into one span; these appear as combined keys, e.g. `PSA.54.2+PSA.54.3`.
- The NIV omits textually disputed verses (e.g. Matt 17:21); these appear as empty strings.
- Verse numbering differs between translations (e.g. NB88 PSA.91 has no verse 4).

## Scraping an entire Bible

`scrape_entire_bible.py` fetches every book for one translation and saves each as a JSON file.

```bash
python scrape_entire_bible.py
python scrape_entire_bible.py --translation-id 100 --lang english --include-headings --rate-limit 0.5
```

| Flag | Default | Description |
|------|---------|-------------|
| `--translation-id` | `102` | bible.com translation ID |
| `--lang` | `norwegian` | Book name language (`norwegian` or `english`), used only in filenames |
| `--include-headings` | off | Include section headings in JSON output |
| `--rate-limit` | `0.1` | Seconds to sleep between chapter requests |

Output: `bible_<translation-id>/`, one file per book named `01_GEN_Genesis.json` etc. Already-complete books are skipped; partially scraped books (file exists but chapters are missing) are automatically filled in on rerun.

## Scraping multiple Bibles in parallel

`scrape_all_bibles.py` scrapes all configured translations concurrently using a thread pool.

```bash
python scrape_all_bibles.py
```

Translations and worker count are configured at the top of the file (`TRANSLATIONS`, `MAX_WORKERS`, `RATE_LIMIT`). Always runs with `include_headings=True`. Output follows the same format as above but in per-translation directories named `bible_<id>_<name>/`. Incomplete books are detected and filled in automatically on rerun.

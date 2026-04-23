# Bible Scraper

A Python module for scraping Bible verse text from [bible.com](https://www.bible.com). Fetch single verses, verse ranges, chapters, or entire books. Returns plain Python dicts so you can pipe the data wherever you need it.

## Disclaimer

This tool is for personal, non-commercial use only. Bible text on bible.com is copyrighted by the respective publishers and licensors. By using this scraper you take full responsibility for ensuring your use complies with bible.com's terms of service, applicable copyright law, and the licensing terms of each translation. The author provides no warranty and accepts no liability for any use of this software or the data it produces.

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

# Whole chapter — optionally include section headings and/or footnotes
fetch_chapter("PSA", 23, 102)
fetch_chapter("GEN", 6, 102, include_headings=True)
# -> {"GEN.6.1": "Da nå menneskene...", ...,
#     "headings": {"GEN.6.1": "Menneskenes ondskap", "GEN.6.9": "Noah", ...}}

fetch_chapter("HOS", 1, 102, include_footnotes=True)
# -> {"HOS.1.2": "...horkvinne* og horebarn...", ...,
#     "footnotes": {"HOS.1.2": "3:1. 5Mos 31:16. ... *profetens ekteskap skal være...", ...}}

# Whole book
fetch_book("JON", 102, include_headings=True, include_footnotes=True, rate_limit=0.5)

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

### Footnotes

`fetch_chapter` and `fetch_book` accept `include_footnotes=True`. When set, a `"footnotes"` key is added mapping each USFM key to its footnote text. Only verses that actually have a footnote appear in the dict.

Footnote behaviour differs by translation:

**NB88 (id 102):** All notes in this translation are cross-references, with commentary footnotes embedded inline and prefixed by `*`. When a verse contains such a footnote, the full note text for that verse is collected (cross-references and commentary together). The `*` in the output marks where the commentary begins, e.g.:

```python
"HOS.1.2": "3:1. 5Mos 31:16. Dom 2:17. Esek 16:15 ff. *profetens ekteskap skal være et bilde på Herrens forhold til det troløse Israel."
"HOS.1.9": "*ikke mitt folk. 2:1 ff. **Se 2Mos 3:14 f. Jer 31:33. Joh 8:28."
```

**All other translations:** Only `note.f` elements are collected — these are commentary footnotes (translation notes, alternative readings, manuscript variants), excluding cross-references. Multiple footnotes on the same verse are joined with ` / `, e.g.:

```python
# ESV
"JHN.1.11": "Greek to his own things; that is, to his own domain, or to his own people / People is implied in Greek"
"JON.1.17": "Ch 2:1 in Hebrew / Or had appointed"

# NIV
"ROM.8.3": "In contexts like this, the Greek word for flesh (sarx) refers to the sinful state of human beings..."
```

**Per-translation coverage:** ESV, NIV, BGO, and Bibel2011 have rich footnote content. NASB1995 has concise literal-translation notes. KJV, Bibel1930, and NKJV have no footnote data on bible.com and will always return an empty `"footnotes"` dict.

**Known limitations:** Notes attached to a section or block rather than a specific verse (e.g. the ESV note covering John 7:53–8:11, or BGO's psalm header notes) are not captured, as they have no verse span to anchor to in the HTML.

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
| `--include-footnotes` | off | Include footnotes in JSON output |
| `--rate-limit` | `0.1` | Seconds to sleep between chapter requests |

Output: `bible_<translation-id>/`, one file per book named `01_GEN_Genesis.json` etc. Already-complete books are skipped; partially scraped books (file exists but chapters are missing) are automatically filled in on rerun.

## Scraping multiple Bibles in parallel

`scrape_all_bibles.py` scrapes all configured translations concurrently using a thread pool.

```bash
python scrape_all_bibles.py
```

Translations and worker count are configured at the top of the file (`TRANSLATIONS`, `MAX_WORKERS`, `RATE_LIMIT`). Always runs with `include_headings=True` and `include_footnotes=True`. Output follows the same format as above but in per-translation directories named `bible_<id>_<name>/`. Incomplete books are detected and filled in automatically on rerun.

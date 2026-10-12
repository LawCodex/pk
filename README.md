# LawCodex — Pakistan (`pk`)

Federal legislation of the Islamic Republic of Pakistan as plain Markdown, one file per law, taken
from **The Pakistan Code** (<https://pakistancode.gov.pk>), the official online code of federal laws
maintained by the Ministry of Law and Justice, which publishes laws "in revised form" (amendments
incorporated, with amendment footnotes).

Part of [LawCodex](https://github.com/LawCodex): the laws of every country as Markdown in git.

Retrieved: 2026-10-12. **982 files.**

## Contents

| Category | Directory | Files |
|---|---|---:|
| Constitution of the Islamic Republic of Pakistan, 1973 (revised, up to the 27th Amendment, 2025) | `constitution/` | 1 |
| Acts (incl. the Pakistan Penal Code, Code of Criminal Procedure, Code of Civil Procedure) | `laws/<year>/` | 669 |
| Ordinances | `laws/<year>/` | 302 |
| President's Orders / Orders | `laws/<year>/` | 9 |
| Rules of Business, 1973 | `laws/1973/` | 1 |
| **Total** | | **982** |

The laws span 1838–2026 (158 year directories). All texts are in English.

39 files carry `status: repealed`: the Pakistan Code keeps some repealed laws in its list and says so
in the title (e.g. "… (Repealed by Act IV of 2012, s.7)"). All other files are `in_force` as listed
by the source, which notes that all its texts are "under review".

## Not covered

- **50 laws whose PDF is a scanned image** (no text layer), mostly repealed laws, plus 2026
  ordinances (e.g. *Defence Industrial Production and Regulatory Authority of Pakistan Ordinance,
  2026*, *Pakistan Nursing and Midwifery Council Ordinance, 2025*). No OCR.
- **5 laws whose PDF could not be downloaded** (server error): Government Management of Private
  Estates Act, 1892; Marriage Functions (Ostentatious Displays) Ordinance, 1999; Motor Vehicles
  (Drivers) Ordinance, 1942; Representation of People Act, 1976; Suits Valuation Act, 1887.
- **Urdu texts.** The Pakistan Code publishes Urdu translations of 50 laws (incl. the Constitution) as
  PDFs, but their text layer is empty or unusable (glyphs without Unicode mapping), so they are not
  included.
- Provincial laws (each province has its own code) and subordinate legislation (rules, SROs).

## Structure

```
constitution/constitution-of-the-islamic-republic-of-pakistan.md
laws/<year>/<year>-<number>-<slug>.md     e.g. laws/1860/1860-xlv-pakistan-penal-code-ppc-1860-under-review.md
```

`<number>` is the law number as given by the source (`xlv` for Act XLV, `ordinance-no-li`, …).

Front matter: `title`, `identifier` (e.g. `XLV of 1860`), `type` (`constitution`, `act`, `ordinance`,
`order`, `code`, `rules`), `jurisdiction`, `language` (`en`), `date` (promulgation date given by the
source), `last_amended` (year of the source's "Updated Date", when given), `status`, `category`
(the source's subject category), `source` (law page), `source_pdf`, `retrieved`.

Body: text extracted from the official PDF (`pdftotext -layout`) and structured:

- the arrangement of sections ("CONTENTS") at the top is kept as a plain list;
- `PART …` → `##`, `CHAPTER …` → `###`, each section/article `12. Heading.—(1) text` →
  `#### 12. Heading` followed by its text; schedules → `##` (their numbered items are not headings);
- amendment markers are kept as printed (`1[inserted words]`, `<sup>1</sup>` where the marker was
  printed on its own line); the page footnotes that explain them ("Subs. by … Act, 2010 …") are
  kept as `> ` quote lines after the section where they occur — footnote numbers restart on every
  page, as in the source;
- running heads, page numbers and "Page n of m" footers are removed; tables detected as such are kept
  in fenced blocks, other tables are flattened.

Heading detection is heuristic: in 23 files (mostly short or unusually formatted texts) no section
headings were detected and the text is plain paragraphs.

## Sources

- The Pakistan Code — <https://pakistancode.gov.pk/english/>: alphabetical index
  (`LGu0xAD?alp=<letter>&page=1&action=inactive`), law pages, PDFs under `/pdffiles/`.
- robots.txt only disallows `/pdffiles/` for Googlebot; no Crawl-delay. The site's disclaimer says the
  texts are for information and that the Gazette is authoritative; no terms restricting reuse were
  found. ≤ 3 parallel requests, 1-second delay per worker.

## Licence

Laws of Pakistan are official public texts. This compilation adds no copyrightable content.

## Regenerate

```
pip install -r scripts/requirements.txt
python scripts/pk_fetch.py      # caches index pages, law pages and PDFs under ../_raw/pk
python scripts/pk_convert.py .  # writes the Markdown files
```

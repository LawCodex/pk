#!/usr/bin/env python3
"""Convert the cached Pakistan Code PDFs (see pk_fetch.py) into Markdown files in the repo.

Usage: pk_convert.py [REPO_DIR]
"""
import json, os, re, sys, datetime, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
from pk_pdfmd import to_markdown, pdf_pages

RAW = os.environ.get("RAW", os.path.join(os.path.dirname(__file__), "..", "..", "_raw", "pk"))
REPO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..")
RETRIEVED = os.environ.get("RETRIEVED", datetime.date.today().isoformat())
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}


def slug(s, n=80):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    if len(s) > n:
        s = s[:n].rsplit("-", 1)[0]
    return s


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_date(s):
    if not s:
        return None
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", s.strip())
    if m and m.group(1).lower() in MONTHS:
        try:
            return datetime.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))).isoformat()
        except ValueError:
            return None
    return None


def law_type(title):
    t = title.lower()
    if "constitution of the islamic republic" in t and "amendment" not in t:
        return "constitution"
    for k, v in [("ordinance", "ordinance"), ("president's order", "order"), ("president’s order", "order"),
                 (" order", "order"), ("regulation", "regulation"), ("rules", "rules"), ("code", "code"),
                 ("act", "act")]:
        if re.search(r"\b" + k.strip() + r"\b", t):
            return v
    return "act"


def main():
    idx = json.load(open(f"{RAW}/index.json"))
    stats = {"ok": 0, "scanned": [], "missing": []}
    seen = set()
    for r in idx:
        title = r["title"]
        pdf = r.get("pdf")
        local = f"{RAW}/pdf/{os.path.basename(pdf)}" if pdf else None
        if not local or not os.path.exists(local):
            stats["missing"].append(title)
            continue
        pages = pdf_pages(local)
        chars = sum(len(re.sub(r"\s", "", p)) for p in pages)
        if chars < 100 * len(pages):
            stats["scanned"].append({"title": title, "url": r.get("url"), "pdf": pdf, "pages": len(pages)})
            continue
        typ = law_type(title)
        date = parse_date(r.get("promulgation"))
        ym = re.search(r"\b(1[6-9]\d\d|20\d\d)\b(?!.*\b(1[6-9]\d\d|20\d\d)\b)", re.sub(r"\(.*?\)", "", title)) or \
            re.search(r"\b(1[6-9]\d\d|20\d\d)\b", title)
        year = (date or "")[:4] or (ym.group(1) if ym else "undated")
        if ym and typ != "constitution":
            year = ym.group(1)
        num = r.get("number") or ""
        if typ == "constitution":
            rel = "constitution/constitution-of-the-islamic-republic-of-pakistan.md"
        else:
            nslug = slug(num.split(" of ")[0]) if num else ""
            base = f"{year}-{nslug + '-' if nslug else ''}{slug(re.sub(r',?\s*' + year + r'\s*$', '', title))}"
            rel = f"laws/{year}/{base[:100].rstrip('-')}.md"
        if rel in seen:
            rel = rel[:-3] + "-" + slug(os.path.basename(pdf)[-12:-4]) + ".md"
        seen.add(rel)
        body = to_markdown(local)
        upd = re.search(r"Updated Date:\s*(\d{4})", r.get("meta", ""))
        fm = ["---", f"title: {q(title)}"]
        if num:
            fm.append(f"identifier: {q(num)}")
        fm.append(f"type: {typ}")
        fm += ["jurisdiction: pk", "language: en"]
        if date:
            fm.append(f"date: {date}")
        if upd:
            fm.append(f"last_amended: {q(upd.group(1))}")
        fm.append("status: " + ("repealed" if re.search(r"\(\s*repeal(ed)?\s+by", title, re.I) else "in_force"))
        if r.get("category"):
            fm.append(f"category: {q(r['category'])}")
        fm.append(f"source: {q(r['url'])}")
        fm.append(f"source_pdf: {q(pdf)}")
        fm.append(f"retrieved: {RETRIEVED}")
        fm.append("---")
        md = "\n".join(fm) + "\n\n# " + title + "\n\n" + body
        path = os.path.join(REPO, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
        stats["ok"] += 1
    json.dump(stats, open(f"{RAW}/convert-stats.json", "w"), indent=1, ensure_ascii=False)
    print("written", stats["ok"], "scanned", len(stats["scanned"]), "missing", len(stats["missing"]))


if __name__ == "__main__":
    main()

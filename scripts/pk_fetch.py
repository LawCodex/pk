#!/usr/bin/env python3
"""Fetch the Pakistan Code (https://pakistancode.gov.pk) index pages, law pages and PDFs.

Everything is cached under RAW (default: ../../_raw/pk) so re-runs only fetch what is missing.
Output: RAW/index.json (one record per law, English) and RAW/urdu.json.
"""
import json, os, re, sys, time, html
import requests

UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
BASE = "https://pakistancode.gov.pk/english/"
RAW = os.environ.get("RAW", os.path.join(os.path.dirname(__file__), "..", "..", "_raw", "pk"))
DELAY = 1.0
S = requests.Session()
S.headers["User-Agent"] = UA


def get(url, path, binary=False):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return open(path, "rb").read()
    for attempt in range(6):
        try:
            r = S.get(url, timeout=120)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + ".part", "wb") as f:
                f.write(r.content)
            os.replace(path + ".part", path)
            time.sleep(DELAY)
            return r.content
        except Exception as e:  # network errors through flaky links
            print("retry", attempt, url, e, file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    return None


def clean(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def parse_letter(s):
    out = []
    # only the first list (the page also repeats a navigation block)
    for m in re.finditer(r"<div class='accordion-section-title'[^>]*>\s*<a href=\"(UY2FqaJw1-[^\"]+)\">(.*?)</a>(.*?)<div class='accordion-section-content'[^>]*>(.*?)</div>", s, re.S):
        href, title, _, meta = m.groups()
        meta_t = clean(re.sub(r"<!--.*?-->", "", meta, flags=re.S))
        parts = [p.strip() for p in meta_t.split("|")]
        rec = {"href": href, "title": clean(title), "meta": meta_t}
        if parts:
            rec["category"] = parts[0]
        for p in parts[1:]:
            if p.startswith("Promulgation Date:"):
                rec["promulgation"] = p.split(":", 1)[1].strip().rstrip(".")
            elif re.search(r"\bof\s+\d{4}\b", p) or re.match(r"^[IVXLCDM]+\b", p):
                rec["number"] = p
        out.append(rec)
    return out


def main():
    os.makedirs(RAW, exist_ok=True)
    laws = {}
    for L in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        page = 1
        while True:
            url = f"{BASE}LGu0xAD?alp={L}&page={page}&action=inactive"
            s = get(url, f"{RAW}/index/{L}-{page}.html").decode("utf-8", "replace")
            recs = parse_letter(s)
            new = [r for r in recs if r["href"] not in laws]
            for r in new:
                laws[r["href"]] = r
            print(L, page, len(recs), len(new), file=sys.stderr)
            if f"alp={L}&page={page+1}" in s and new:
                page += 1
            else:
                break
    # law pages -> pdf url
    def one(item):
        href, r = item
        key = re.sub(r"[^A-Za-z0-9]", "_", href)[:120]
        s = get(BASE + href, f"{RAW}/law/{key}.html")
        r["url"] = BASE + href
        if not s:
            return
        s = s.decode("utf-8", "replace")
        m = re.search(r'href="(https?://[^"]*pdffiles/[^"]+\.pdf)"[^>]*target="_top"', s)
        if not m:
            m = re.search(r'ViewerJS/#\.\./pdffiles/([^"]+\.pdf)', s)
            pdf = "https://pakistancode.gov.pk/pdffiles/" + m.group(1) if m else None
        else:
            pdf = m.group(1)
        r["pdf"] = pdf
        if pdf:
            get(pdf, f"{RAW}/pdf/{os.path.basename(pdf)}")

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(3) as ex:
        for i, _ in enumerate(ex.map(one, sorted(laws.items()))):
            if i % 50 == 0:
                print("law", i, len(laws), file=sys.stderr)
    json.dump(sorted(laws.values(), key=lambda r: r["title"]), open(f"{RAW}/index.json", "w"), ensure_ascii=False, indent=1)
    # Urdu
    s = get(BASE + "UHyrdu.php", f"{RAW}/index/urdu.html").decode("utf-8", "replace")
    ur = []
    for m in re.finditer(r'<a href="(https://pakistancode.gov.pk/pdffiles/[^"]+\.pdf)" target="_blank">(.*?)</a>', s, re.S):
        ur.append({"pdf": m.group(1), "title": clean(m.group(2))})
        get(m.group(1), f"{RAW}/pdf-ur/{os.path.basename(m.group(1))}")
    json.dump(ur, open(f"{RAW}/urdu.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Convert a text-layer PDF of a common-law style statute (Pakistan Code) into Markdown body text.

Strategy (pdftotext -layout, page by page):
  * drop running footers ("Page N of M"), lone page numbers;
  * detect the footnote block at the bottom of each page (a footnote number alone at column 0,
    followed by the footnote text) and move footnotes to a quote block after the current
    section;
  * superscript amendment markers printed on their own line are re-attached to the next line
    (e.g. "2" + "[(2A) ..." -> "2[(2A) ...");
  * lines are joined into paragraphs (blank line = paragraph break);
  * PART / CHAPTER / SCHEDULE paragraphs become headings, sections ("12. Heading.__ text")
    become "#### 12. Heading" followed by the text;
  * the table of contents ("arrangement of sections") at the beginning is kept as a plain list;
  * tabular paragraphs (several columns separated by wide gaps) are kept in a fenced block.
"""
import re, subprocess

FOOTER = re.compile(r"^\s*(Page\s+\d+\s+of\s+\d+|\d{1,4}|-\s*\d+\s*-)\s*$", re.I)
FN_START = re.compile(r"^(\d{1,3})\s*$")
SUP_LINE = re.compile(r"^\s{2,}(\d{1,3}(?:\s+\d{1,3})*)\s*$")
PART = re.compile(r"^\[?\s*(?:\d{1,3}\s*\[)?\s*(PART|Part)\s+[IVXLC\d]+[A-Z]?\b")
CHAP = re.compile(r"^\[?\s*(?:\d{1,3}\s*\[)?\s*(CHAPTER|Chapter)\s+[IVXLC\d]+[A-Z]?\b")
SCHED = re.compile(r"^\[?\s*(?:\d{1,3}\s*\[)?\s*((THE\s+)?([A-Z]+\s+)?SCHEDULE|ANNEX(URE)?|APPENDIX|FORM)\b")
SECTION = re.compile(r"^((?:<sup>\d+</sup>|\d{1,3}(?=\s*\[))?\s*\[?\s*)(\d{1,4}[A-Z]{0,3}(?:-[A-Z])?)\.\s+(.*)$", re.S)
DELIMS = ["__", ".—", ".–", ".-", ". —", ". –", ":—", ":-", "—", "–"]
TOCLINE = re.compile(r"^\[?\d{1,4}[A-Z]{0,3}\.\s+\S")


def pdf_pages(path):
    out = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", path, "-"], capture_output=True)
    txt = out.stdout.decode("utf-8", "replace")
    return txt.split("\f")


def split_page(page):
    lines = page.split("\n")
    # strip trailing blank/footer lines
    while lines and (not lines[-1].strip() or FOOTER.match(lines[-1])):
        lines.pop()
    # remove footer anywhere in last few lines
    lines = [l for i, l in enumerate(lines) if not (re.match(r"^\s*Page\s+\d+\s+of\s+\d+\s*$", l, re.I))]
    # footnote block: first line (in bottom 60% of page) that is a bare number at col 0
    fn_at = None
    n = len(lines)
    for i in range(n):
        if FN_START.match(lines[i]) and i + 1 < n and lines[i + 1].strip() and i > n * 0.25:
            # the following text must not look like a section heading
            fn_at = i
            break
    body, notes = lines, []
    if fn_at is not None:
        body = lines[:fn_at]
        cur = None
        for l in lines[fn_at:]:
            m = FN_START.match(l)
            if m:
                cur = [m.group(1), ""]
                notes.append(cur)
            elif l.strip():
                if cur is None:
                    cur = ["", ""]
                    notes.append(cur)
                cur[1] = (cur[1] + " " + l.strip()).strip()
        notes = [f"{a} {b}".strip() for a, b in notes if b or a]
    # re-attach superscript marker lines
    fixed = []
    pending = None
    for l in body:
        m = SUP_LINE.match(l)
        if m and len(m.group(1)) <= 7:
            pending = (pending + " " if pending else "") + m.group(1).replace(" ", "")
            continue
        if pending and l.strip():
            ind = len(l) - len(l.lstrip())
            l = " " * ind + (pending if l.lstrip().startswith("[") else "<sup>" + pending + "</sup>") + l.lstrip()
            pending = None
        fixed.append(l)
    return fixed, notes


SECSTART = re.compile(r"^(<sup>\d+</sup>|\d{1,3}(?=\s*\[))?\s*\[?\d{1,4}[A-Z]{0,3}\.\s+\S")


def is_heading_line(l):
    st = l.strip()
    ind = len(l) - len(l.lstrip())
    if len(st) > 120:
        return False
    if (PART.match(st) or CHAP.match(st)) and (ind >= 8 or len(st) < 60):
        return True
    if ind >= 10 and re.search(r"[A-Z]{3}", st) and st.upper() == st and not re.match(r"^\(?[a-z0-9]+\)", st):
        return True
    return False


def is_tabular(lines):
    rows = [l.strip() for l in lines if l.strip()]
    if len(rows) < 2:
        return False
    multi = sum(1 for r in rows if len(re.findall(r"\S {3,}(?=\S)", r)) >= 2)
    return multi >= max(2, len(rows) * 0.6)


def running_headers(pages):
    """lines repeated at the top of many pages (running heads) -> set of normalized texts"""
    from collections import Counter
    c = Counter()
    for p in pages:
        top = [l for l in p.split("\n") if l.strip()][:2]
        for l in top:
            c[re.sub(r"\d+", "#", " ".join(l.split()))] += 1
    n = len(pages)
    return {k for k, v in c.items() if v >= 3 and (v >= 0.2 * n or re.search(r"_{5,}\s*$", k))}


def paragraphs(pages):
    """yield ('p', lines) or ('fn', text) items"""
    heads = running_headers(pages)
    pages = ["\n".join(l for l in p.split("\n") if re.sub(r"\d+", "#", " ".join(l.split())) not in heads
                       and not re.fullmatch(r"\s*\.\.\s*", l)) for p in pages]
    items = []
    cur = []
    for pi, page in enumerate(pages):
        body, notes = split_page(page)
        # page break: decide whether first para continues the last one
        first = next((l for l in body if l.strip()), None)
        if cur and first is not None:
            last = cur[-1].rstrip()
            ind = len(first) - len(first.lstrip())
            if last.endswith((".", ":", ";", "]")) and (ind >= 4 or first.strip()[:1].isupper() or first.strip().startswith("(")):
                items.append(("p", cur))
                cur = []
        for l in body:
            if not l.strip():
                if cur:
                    items.append(("p", cur))
                    cur = []
                continue
            st = l.strip()
            ind = len(l) - len(l.lstrip())
            if is_heading_line(l):
                if cur:
                    items.append(("p", cur))
                items.append(("p", [l]))
                cur = []
                continue
            if cur:
                prev = cur[-1]
                pind = len(prev) - len(prev.lstrip())
                pend = prev.rstrip()[-1:]
                if pend in ".;:]_—–" and (ind - pind >= 3 or SECSTART.match(st)):
                    items.append(("p", cur))
                    cur = []
            cur.append(l)
        for nt in notes:
            items.append(("fn", nt))
    if cur:
        items.append(("p", cur))
    # footnotes were emitted at page end, possibly in the middle of a paragraph that continues;
    # move each footnote after the next paragraph boundary is handled by the renderer.
    return items


def join(lines):
    s = " ".join(re.sub(r"\s+", " ", l.strip()) for l in lines)
    s = re.sub(r"(\w)- (\w)", lambda m: m.group(0) if m.group(2).isupper() else m.group(1) + "-" + m.group(2), s)
    return s.strip()


def esc(s):
    # avoid accidental markdown: leading '#', '>', list markers like '1.' are fine as text
    if s.startswith(("#", ">", "+ ", "- ", "* ", "=")):
        return "\\" + s
    return s


def split_heading(rest):
    cands = []
    for d in DELIMS:
        i = rest.find(d)
        if 0 < i <= 250:
            if d in ("—", "–") and i > 160:
                continue
            cands.append((i, i + len(d)))
    m = re.match(r"^(.{3,200}?[a-z\)\]])\.\s+(?=[A-Z(\[\"“‘0-9])", rest, re.S)
    if m:
        cands.append((len(m.group(1)), m.end()))
    if not cands:
        return None, rest
    i, j = min(cands)
    title = rest[:i].strip()
    if not title or len(title) < 2:
        return None, rest
    return title.rstrip(".").strip() + ".", rest[j:].strip()


def to_markdown(pdf_path, level_base=2):
    pages = pdf_pages(pdf_path)
    items = paragraphs(pages)
    paras = [(k, join(v) if k == "p" else v, v if k == "p" else None) for k, v in items]
    # locate first section heading with body text (start of the body)
    first_sec = None
    for idx, (k, t, raw) in enumerate(paras):
        if k == "p":
            m = SECTION.match(t)
            if m and m.group(2) == "1":
                title, body = split_heading(m.group(3))
                if title and body:
                    first_sec = idx
                    break
    toc_end = -1
    if first_sec is not None:
        for idx in range(first_sec):
            k, t, raw = paras[idx]
            if k == "p" and (TOCLINE.match(t) or re.search(r"SCHEDULE", t) or any(TOCLINE.match(l.strip()) for l in raw)):
                toc_end = idx
        if toc_end >= 0:
            # TOC entries must be dense; otherwise there is no TOC
            n_toc = sum(1 for k, t, r in paras[:toc_end + 1] if k == "p" and any(TOCLINE.match(l.strip()) for l in r))
            if n_toc < 3:
                toc_end = -1
    H = lambda n: "#" * min(6, level_base + n)
    out = []
    pending_fn = []
    in_toc_list = False
    in_sched = False

    def flush_fn():
        if pending_fn:
            out.append("")
            for f in pending_fn:
                out.append("> " + f)
            out.append("")
            pending_fn.clear()

    for idx, (k, t, raw) in enumerate(paras):
        if k == "fn":
            pending_fn.append(t)
            continue
        if not t:
            continue
        if idx <= toc_end:
            out.append(esc(t) + "  ")
            in_toc_list = True
            continue
        if in_toc_list:
            out.append("")
            in_toc_list = False
        if is_tabular(raw):
            out.append("")
            out.append("```")
            base = min(len(l) - len(l.lstrip()) for l in raw if l.strip())
            out.extend(l[base:].rstrip() for l in raw)
            out.append("```")
            out.append("")
            continue
        short = len(t) < 160
        if short and PART.match(t):
            flush_fn()
            out += ["", H(0) + " " + t, ""]
            continue
        if short and CHAP.match(t):
            flush_fn()
            out += ["", H(1) + " " + t, ""]
            continue
        if short and SCHED.match(t) and t.upper()[:40] == t[:40]:
            flush_fn()
            out += ["", H(0) + " " + t, ""]
            in_sched = True
            continue
        m = SECTION.match(t)
        if m and in_sched and m.group(2) == "1" and any(d in m.group(3)[:200] for d in ("__", ".—", ".–", ".-", ". —", ". –")):
            in_sched = False  # body restarts after a table of contents listing schedules
        if m and idx > toc_end and not in_sched:
            title, body = split_heading(m.group(3))
            if title:
                flush_fn()
                pre = m.group(1).strip()
                pre = re.sub(r"^(\d{1,3})\s*(?=\[|$)", r"<sup>\1</sup>", pre)
                out += ["", H(2) + " " + (pre + m.group(2)).strip() + ". " + title, ""]
                if body:
                    out += [esc(body), ""]
                continue
        out += [esc(t), ""]
    flush_fn()
    md = "\n".join(out)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return md


if __name__ == "__main__":
    import sys
    print(to_markdown(sys.argv[1]))

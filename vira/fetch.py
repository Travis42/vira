import json
import re
import time
from html.parser import HTMLParser

import requests

WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")


def load_cfg(path="book.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def api_get(api, **params):
    for attempt in range(4):
        r = requests.get(api, params={"action": "parse", "format": "json", **params},
                         headers={"User-Agent": "vira/1.0"}, timeout=60)
        if r.status_code == 429:  # wikisource rate-limits bursts
            time.sleep(5 * (attempt + 1))
            continue
        break
    r.raise_for_status()
    return r.json()


def subpage_links(wikitext):
    """(target, display) for wikilinks containing '/', deduped, first-appearance order."""
    seen, out = set(), []
    for m in re.finditer(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]", wikitext):
        t = m.group(1).strip()
        if "/" in t and t not in seen:
            seen.add(t)
            out.append((t, (m.group(2) or t).strip()))
    return out


def clean_wikitext(wikitext):
    """Return list of {t: 'h'|'p', text} structural items."""
    t = wikitext
    t = re.sub(r"<ref\s*/\s*>", "", t)
    t = re.sub(r"<ref[ >].*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    # strip templates innermost-out, repeatedly
    while True:
        nt = re.sub(r"\{\{[^{}]*\}\}", "", t)
        if nt == t:
            break
        t = nt
    t = t.replace("<br>", "\n").replace("<br />", "\n").replace("<br/>", "\n")
    t = re.sub(r"<[^>]+>", "", t)
    import html
    t = html.unescape(t)
    t = re.sub(r"\[\[([^|\]]+)\]\]", r"\1", t)                      # [[a]] -> a
    t = re.sub(r"\[\[[^\]]*\|([^\]]+)\]\]", r"\1", t)               # [[a|b]] -> b
    t = re.sub(r"\[[^\s\]]+\s+([^\]]+)\]", r"\1", t)          # [url label] -> label
    t = re.sub(r"\[https?://[^\]]*\]", "", t)                       # bare [url]
    t = re.sub(r"'{2,}", "", t)                                     # bold/italic
    items = []
    for line in t.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 3:
            continue
        h = re.fullmatch(r"={1,6}\s*(.+?)\s*={1,6}", line)
        items.append({"t": "h", "text": h.group(1)} if h else {"t": "p", "text": line})
    return items


def tokens(text):
    return [w.lower() for w in WORD_RE.findall(text)]


class _TextExtract(HTMLParser):
    """Readable text from rendered wikisource HTML, skipping nav junk.
    shortcut: page-transcluded books must be fetched as rendered HTML, not wikitext."""
    SKIP = ("ws-noexport", "noprint", "searchaux", "mw-editsection", "reference",
            "printfooter", "catlinks")
    HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._buf = []
        self._skip = []      # stack of open tags while skipping
        self._heading = []   # stack of open heading tags

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self._skip.append(tag)
        elif self._skip:
            self._skip.append(tag)
        elif any(s in dict(attrs).get("class", "") for s in self.SKIP):
            self._skip.append(tag)
        else:
            if tag in self.HEADINGS:
                self._heading.append(tag)
                self._buf.append("\x01")
            if tag in self.HEADINGS | {"p", "br", "li", "tr", "div"}:
                self._buf.append("\x02")

    def handle_endtag(self, tag):
        if self._skip:
            self._skip.pop()
            return
        if tag in self.HEADINGS and self._heading:
            self._heading.pop()
            self._buf.append("\x01")
        if tag in self.HEADINGS | {"p", "li", "tr", "div"}:
            self._buf.append("\x02")

    def handle_data(self, data):
        if not self._skip:
            self._buf.append(data)

    def items(self):
        items = []
        for line in "".join(self._buf).split("\x02"):
            is_h = "\x01" in line
            line = re.sub(r"\s+", " ", line).strip().strip("\x01").strip()
            if len(line) < 3 or line.startswith(".mw-parser-output"):
                continue
            if is_h and line.lower() == "notas":  # endnotes/references junk
                break
            items.append({"t": "h" if is_h else "p", "text": line})
        return items


def clean_html(html):
    p = _TextExtract()
    p.feed(html)
    return p.items()


def run(refresh=False):
    cfg = load_cfg()
    try:
        with open("data/chapters.json", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"chapters": []}
    have = {c["title"]: c for c in data["chapters"]}
    work = api_get(cfg["api"], page=cfg["work"], prop="wikitext")["parse"]["wikitext"]["*"]
    links = subpage_links(work)
    wanted = cfg["chapters"]
    for link, display in links:
        if wanted != ["all"] and not any(re.match(p + r"\b", display) or re.match(p + r"\b", link)
                                         for p in wanted):
            continue
        if link in have and not refresh:
            print(f"cached: {link}")
            continue
        print(f"fetch: {link}")
        page = api_get(cfg["api"], page=link, prop="wikitext")["parse"]
        wikitext = page["wikitext"]["*"]
        # page-transcluded chapters (ProofreadPage <pages .../>) have no wikitext body
        if re.search(r"<pages\s", wikitext):
            html = api_get(cfg["api"], page=link, prop="text")["parse"]["text"]["*"]
            paras = clean_html(html)
        else:
            paras = clean_wikitext(wikitext)
        data["chapters"] = [c for c in data["chapters"] if c["title"] != link]
        have.pop(link, None)
        data["chapters"].append({
            "title": link,
            "url": f"https://pt.wikisource.org/wiki/{requests.utils.quote(link.replace(' ', '_'))}",
            "paras": paras,
        })
        with open("data/chapters.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"chapters: {len(data['chapters'])}")

import json
import re

from vira.build import TEMPLATE, embed
from vira.fetch import tokens

CHAPTERS = {"chapters": [{
    "title": "Capítulo I",
    "url": "https://pt.wikisource.org/wiki/X",
    "paras": [
        {"t": "h", "text": "Capítulo I"},
        {"t": "p", "text": "O descobrimento da Índia foi grande. O rei mandou navios, e a rainha disse que sim."},
    ],
}]}
GLOSS = {"o": "the", "descobrimento": "discovery", "da": "of the", "índia": "India",
         "foi": "was", "grande": "great", "rei": "king", "mandou": "sent",
         "navios": "ships", "e": "and", "a": "the", "rainha": "queen",
         "disse": "said", "que": "that / which", "sim": "yes"}


def test_integration_build_coverage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "book.json").write_text(json.dumps(
        {"work": "W", "model": "m", "fallback_model": "f"}))
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "chapters.json").write_text(
        json.dumps(CHAPTERS, ensure_ascii=False))
    (tmp_path / "data" / "glossary.json").write_text(
        json.dumps(GLOSS, ensure_ascii=False))
    import vira.build
    vira.build.run()
    para_tokens = tokens("".join(p["text"] for p in CHAPTERS["chapters"][0]["paras"]
                                 if p["t"] == "p"))
    html = (tmp_path / "dist" / "index.html").read_text()
    # the page renders spans client-side; verify the embedded glossary drives
    # >=99% interactive coverage by replaying the frontend's wrap rule
    m = re.search(r"const GLOSS = (\{.*?\});\n", html, re.S)
    embedded = json.loads(m.group(1).replace("\\/", "/"))
    assert embedded == GLOSS
    glossed = sum(1 for t in para_tokens if t in embedded)
    assert glossed >= 0.99 * len(para_tokens)
    assert "__CHAPTERS__" not in html and "https://api" not in html


def test_coverage_function(tmp_path):
    from vira.gloss import coverage
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "chapters.json").write_text(json.dumps(CHAPTERS, ensure_ascii=False))
    (tmp_path / "data" / "glossary.json").write_text(json.dumps(GLOSS, ensure_ascii=False))
    hit, total = coverage(str(tmp_path / "data" / "chapters.json"),
                          str(tmp_path / "data" / "glossary.json"))
    assert (hit, total) == (15, 17)  # heading adds "capítulo", "i"

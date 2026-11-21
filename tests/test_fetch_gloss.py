import json

from vira.build import embed
from vira.fetch import clean_wikitext, tokens
from vira.gloss import extract_json, normalize

FIXTURE = """{{Infobox book}}
<!-- comment -->
<ref>a ref</ref> and <ref name=x/> here.
== Capítulo I ==
O <b>descobrimento</b> da {{c|Índia}}foi '''grande'''.
Veja [[Portugal/Especial:algo|Portugal]] e [[Lisboa]].
External [https://x.com site] and bare [https://y.com].<br>New line.
"""


def test_clean_wikitext():
    items = clean_wikitext(FIXTURE)
    assert {"t": "h", "text": "Capítulo I"} in items
    texts = [i["text"] for i in items]
    assert "and here." in texts
    assert "O descobrimento da foi grande." in texts
    assert "Veja Portugal e Lisboa." in texts
    assert "External site and bare ." in texts
    assert "New line." in texts
    assert not any("ref" in t or "{{" in t or "<" in t for t in texts)


def test_tokens():
    toks = tokens("O descobrimento da Índia foi grande, d'El-Rei — navios")
    assert toks == ["o", "descobrimento", "da", "índia", "foi", "grande", "d'el", "rei", "navios"]


def test_extract_json_noisy():
    noisy = 'Sure! Here is the JSON:\n```json\n{"de": "of", "que": "that / which"}\n``` hope it helps'
    assert json.loads(extract_json(noisy)) == {"de": "of", "que": "that / which"}
    assert extract_json('{"a": {"b": 1}, "c": [2]}') == '{"a": {"b": 1}, "c": [2]}'


def test_normalize():
    assert normalize("  of   the  ") == "of the"
    assert len(normalize("x" * 100)) == 60


def test_embed_escapes_script_close():
    s = embed({"a": "</script><b>x</b>"})
    assert "</script>" not in s
    assert json.loads(s.replace("\\/", "/")) == {"a": "</script><b>x</b>"}

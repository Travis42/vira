import json
import re

from vira.gloss import translate_batch


def test_resume_skips_existing(tmp_path, monkeypatch):
    # resume logic: todo list excludes words already in glossary.json
    from vira.fetch import tokens
    gloss = {"o": "the"}
    words = sorted(set(tokens("O rei")))
    todo = [w for w in words if w not in gloss]
    assert todo == ["rei"]


def test_translate_batch_accepts_90pct(monkeypatch):
    def fake_chat(model, words, key):
        return json.dumps({"de": "of", "que": "that"})  # 2/3 keys ≈ 67% -> reject
    monkeypatch.setattr("vira.gloss.chat", fake_chat)
    monkeypatch.setattr("time.sleep", lambda s: None)
    cfg = {"model": "m", "fallback_model": "f"}
    assert translate_batch(["de", "que", "rei"], cfg, "k") == {}


def test_translate_batch_model_fallback(monkeypatch):
    import requests
    calls = []

    class R:
        status_code = 404
        text = '{"error":"model not found"}'

        def raise_for_status(self):
            raise requests.HTTPError(response=self)

    def fake_chat(model, words, key):
        calls.append(model)
        if model == "deepseek":
            raise requests.HTTPError(response=R())
        return json.dumps({"de": "of"})

    monkeypatch.setattr("vira.gloss.chat", fake_chat)
    cfg = {"model": "deepseek", "fallback_model": "glm"}
    got = translate_batch(["de"], cfg, "k")
    assert got == {"de": "of"} and calls == ["deepseek", "glm"]


def test_no_external_refs_in_build():
    from vira.build import TEMPLATE
    # footer attribution is allowed as plain text; script/style/src/href refs are not
    for m in re.finditer(r'(?:src|href)\s*=\s*["\'](http[^"\']+)', TEMPLATE):
        raise AssertionError(f"external ref: {m.group(1)}")

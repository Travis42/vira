import json

from vira.fetch import data_paths, run, work_slug

ECA_CFG = {"work": "A Cidade e as Serras", "api": "https://pt.wikisource.org/w/api.php",
           "chapter_pages": ["A Cidade e as Serras/I", "A Cidade e as Serras/II"]}
CHAGAS_CFG = {"work": "Os descobrimentos portuguezes e os de Colombo",
              "api": "https://pt.wikisource.org/w/api.php",
              "chapters": ["Capítulo I"]}
WIKI_ONE = {"parse": {"wikitext": {"*": "== I ==\nO meu amigo nasceu n'um palacio."}}}
WIKI_PAGES = {"parse": {"wikitext": {"*": '<pages index="x.pdf" from=15 to=36 header=1/>'}}}
HTML_ONE = {"parse": {"text": {"*": "<p>O texto renderizado do capitulo.</p>"}}}


def test_work_slug():
    assert work_slug(ECA_CFG) == "a-cidade-e-as-serras"
    assert work_slug(CHAGAS_CFG) == "os-descobrimentos-portuguezes-e-os-de-colombo"
    assert work_slug({"work": "  Odd  --Punct!! "}) == "odd-punct"
    ch, gl = data_paths(ECA_CFG)
    assert ch == "data/a-cidade-e-as-serras/chapters.json"
    assert gl == "data/a-cidade-e-as-serras/glossary.json"


def _write_cfg(tmp_path, cfg):
    (tmp_path / "book.json").write_text(json.dumps(cfg), encoding="utf-8")


def test_chapter_pages_explicit_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_cfg(tmp_path, ECA_CFG)
    calls = []

    def fake_api_get(api, **params):
        page, prop = params["page"], params["prop"]
        calls.append((page, prop))
        if prop == "text":
            return HTML_ONE
        return WIKI_PAGES if page.endswith("/I") else WIKI_ONE

    monkeypatch.setattr("vira.fetch.api_get", fake_api_get)
    run()
    # no work-page wikitext enumeration call in explicit mode
    assert all(page != ECA_CFG["work"] for page, _ in calls)
    data = json.loads((tmp_path / "data" / "a-cidade-e-as-serras" / "chapters.json")
                      .read_text(encoding="utf-8"))
    assert [c["title"] for c in data["chapters"]] == ECA_CFG["chapter_pages"]
    by_title = {c["title"]: c for c in data["chapters"]}
    # <pages> page went through the rendered-HTML path
    assert by_title["A Cidade e as Serras/I"]["paras"] == [{"t": "p", "text": "O texto renderizado do capitulo."}]
    # plain-wikitext page through clean_wikitext
    assert {"t": "h", "text": "I"} in by_title["A Cidade e as Serras/II"]["paras"]
    assert all(c["url"].startswith("https://pt.wikisource.org/wiki/") for c in data["chapters"])


def test_enumeration_mode_regression(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_cfg(tmp_path, CHAGAS_CFG)
    work_wikitext = "Intro. Veja [[Livro/Capítulo I|Capítulo I]] e [[Livro/Capítulo II]]."
    calls = []

    def fake_api_get(api, **params):
        page, prop = params["page"], params["prop"]
        calls.append(page)
        if page == CHAGAS_CFG["work"]:
            return {"parse": {"wikitext": {"*": work_wikitext}}}
        return WIKI_ONE

    monkeypatch.setattr("vira.fetch.api_get", fake_api_get)
    run()
    assert CHAGAS_CFG["work"] in calls          # enumerated from work page
    assert "Livro/Capítulo I" in calls          # matched via "chapters" patterns
    assert "Livro/Capítulo II" not in calls     # not configured
    data = json.loads((tmp_path / "data" / "os-descobrimentos-portuguezes-e-os-de-colombo" / "chapters.json")
                      .read_text(encoding="utf-8"))
    assert [c["title"] for c in data["chapters"]] == ["Livro/Capítulo I"]

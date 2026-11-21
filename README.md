# vira — tap-to-flip PT→EN book reader

A single self-contained HTML page for reading a public-domain Portuguese book
about the Age of Discovery (Pinheiro Chagas, *Os descobrimentos portuguezes e os
de Colombo*, 1881, from pt.wikisource.org). Every word is tappable: tap flips it
to its English gloss, tap again flips it back. Double-tap flips the whole
sentence. No server, no network at runtime — text and glossary are embedded at
build time.

## Pipeline (3 stages, checkpointed, resumable)

```
python3 -m vira fetch   # pt.wikisource MediaWiki API -> data/chapters.json (cached per chapter)
python3 -m vira gloss   # unique vocab -> data/glossary.json via ollama LLM (incremental, resumable)
python3 -m vira build   # -> dist/index.html (single file, works from file://)
python3 -m vira all
```

Or: `make fetch gloss build` / `make test`.

Config lives in `book.json` (work title, API endpoint, chapters, model, batch size).

- **fetch** enumerates chapter subpages from the work page's wikilinks (first-appearance
  order), cleans wikitext (refs, templates, HTML, wikilinks, bold/italic) and caches each
  chapter in `data/chapters.json` — already-fetched chapters are skipped.
- **gloss** builds the unique lowercased vocabulary, translates in batches of ~120 via the
  ollama OpenAI-compatible endpoint (model `deepseek-v4.1-flash`, fallback
  `glm-5.3-flash` on model-not-found only; never OpenRouter), writing
  `data/glossary.json` after every batch. Resume just skips words already present.
  Requires `OLLAMA_API_KEY` in the environment (or `~/.or_zai_env`-style file at
  `/root/.or_zai_env`).
- **build** embeds chapters + glossary into `dist/index.html`.

## Extending to the full book

In `book.json`, flip `"chapters": ["Capítulo I"]` to `"chapters": ["all"]`, then
re-run `make fetch gloss build`. Fetch/gloss are incremental, so only new
chapters/words cost time.

## Tests

`make test` (pytest) — cleaner, tokenizer, JSON extraction, resume, escaping,
no-external-refs, and an integration build coverage check.

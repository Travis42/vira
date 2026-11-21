# SPEC — vira: tap-to-flip PT→EN book reader (v1)

- Date: 2026-11-21 · Author: Operator · Status: approved (Theory "Go" + "build on lab/lab3 via spec + opencode")
- Repo: /root/projects/vira

## 1. What this is
A single self-contained HTML page where the user reads a public-domain Portuguese book about the Age of Discovery. Every word is tappable: tap flips that word to its English gloss in place; tap again flips it back. Double-tap (dblclick) flips the whole sentence. No server, no accounts, no runtime network — book text and the full word→English glossary are embedded in the file at build time.

Book (v1): Pinheiro Chagas, *Os descobrimentos portuguezes e os de Colombo* (1881), full proofread scan-backed text on pt.wikisource.org. MVP renders chapter 1; the pipeline must handle the whole book via config.

## 2. Architecture — 3-stage pipeline, static output
Stages are independent, checkpointed, and resumable. CLI: python3 -m vira {fetch|gloss|build|all}; Makefile targets fetch/gloss/build/test. Config: book.json.

### 2.1 fetch — pt.wikisource → data/chapters.json
- MediaWiki API: action=parse&prop=wikitext (API endpoint https://pt.wikisource.org/w/api.php). Work page: configured title. Enumerate chapter subpages from wikilinks in the work-page wikitext that contain "/" (subpages), deduped, ORDER = first appearance in wikitext.
- For each configured chapter (book.json "chapters": ["Capítulo I ..."] match by regex on link text, or "all"): fetch subpage wikitext, clean it:
  - strip <ref>...</ref> and self-closing refs; strip templates {{...}} repeatedly (innermost-out); strip HTML comments; <br> → newline; strip remaining HTML tags; unescape entities.
  - headings (= x =) → structural items; wikilinks [[target|display]] → display text; bare [url label] → label; strip bare [url].
  - bold/italic quotes removed. Output: list of {t: "h"|"p", text} per chapter, whitespace-normalized. Drop nav/junk paras (<3 chars).
- Cache per chapter (skip refetch if present in chapters.json and --refresh not given) — incremental save.
- Store chapter URL + source title per chapter.

### 2.2 gloss — vocabulary → data/glossary.json (LLM, incremental)
- Token regex: [A-Za-zÀ-ÖØ-öø-ÿ']+ . Unique lowercased set over included chapters.
- Batch translate via ollama OpenAI-compatible endpoint https://api.ollama.com/v1/chat/completions, model deepseek-v4.1-flash (fallback glm-5.3-flash on model-not-found errors ONLY). temperature 0. NEVER OpenRouter (hard rule).
- Auth: OLLAMA_API_KEY env var; if unset, source /root/.or_zai_env (it exports OLLAMA_API_KEY).
- Prompt (system): glossary builder for a 19th-century Portuguese history book; one short English gloss per word (≤4 words); two very different common senses separated by " / " (max 2 senses); verbs as infinitives; include function words (de=of, que=that/which); archaic spellings glossed as the modern word's meaning; proper names → English form or unchanged. Output STRICT JSON object {"word":"gloss"} covering every input word, keys exactly as given.
- Batches of ~120 words. After EVERY batch: merge + write glossary.json (crash cost = one batch). Resume: skip words already in glossary.json. 3 attempts per batch (2s backoff); accept batch if ≥90% keys returned. Stragglers: one-by-one retry pass at the end. Log progress lines to stdout.
- Gloss normalization: trim, collapse whitespace, cap 60 chars.
- Print final coverage report: total unique, glossed, missing.

### 2.3 build — dist/index.html (single file)
- Embed chapters.json content + glossary.json as JS consts (escape "</" as "<\/" in embedded JSON).
- data model: {chapters:[{title,url,paras:[{t,text}]}]}.

### 2.4 Frontend behavior (vanilla JS, no frameworks, no external assets)
- Render paragraphs; wrap every regex-matching word in <span class="w"> with data-o (original), data-g (gloss); words without gloss get class "x" and are NOT interactive.
- Click on .w: toggle textContent between original and gloss; toggle class "f" (flipped style); title attribute shows the hidden side.
- Sentences: split paragraphs on /(?<=[.!?;:])\s+/, wrap in <span class="s">. Double-click inside a sentence flips ALL its words (on if any off, else all off).
- Sticky header: title (book · author · year), buttons: A− / A+ (font size 0.85–1.9rem step 0.12), ◐ dark toggle (html[data-dk]), and "unflip all".
- localStorage persistence: theme (frDk), font size (frFs), scroll position ratio (frPos) — restore on load.
- Mobile-first: viewport meta, touch-action: manipulation, readable serif stack, max-width ~41rem, generous line-height. Light+dark palettes with adequate contrast; flipped words visually distinct (color + underline shadow).
- Zero network on load: no CDN, no fonts, no images. Must work from file:// .

## 3. book.json (v1 default)
{"work":"Os descobrimentos portuguezes e os de Colombo","api":"https://pt.wikisource.org/w/api.php","lang":"pt","gloss_lang":"en","chapters":["Capítulo I"],"model":"deepseek-v4.1-flash","fallback_model":"glm-5.3-flash","batch_size":120}

## 4. Tests (pytest, tests/)
- fetch cleaner: fixture wikitext with refs, nested templates, headings, wikilinks, bold → expected cleaned structure.
- gloss: tokenizer (diacritics, apostrophes, hyphens excluded, mixed case → lowercase); strict-JSON extraction from a wrapped/noisy response; resume skips existing keys; normalization (length cap, whitespace).
- build: embedded JSON escaped ("</script>" safe); output contains no http(s):// references except the footer source attribution link is allowed as plain text; coverage function.
- integration: build from fixture data → count interactive spans vs tokens ≥ 99%.

## 5. Definition of done
- make fetch gloss build produces dist/index.html for chapter 1; pytest -q green; clickable coverage ≥99%; page standalone (no console errors, no network); README.md: what it is, rebuild commands, how to extend to full book (flip "chapters" to "all").

## 6. Non-goals v1 (do NOT build)
Server/components; multi-book UI; context-aware per-instance senses; TTS/audio; EPUB export; user accounts; analytics. Glossary quality = dictionary-level is accepted for v1.

## 7. Blast radius
New repo, no callers, no shared state. Nothing existing breaks.

## 8. Risks
Wikisource markup oddities (poems/tables) → cleaner may need per-case rules; LLM JSON flakiness → retry+solo pass; archaic spellings may gloss imperfectly → accepted v1.

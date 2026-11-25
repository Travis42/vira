import json
import os
import re
import sys
import time

import requests

from .fetch import data_paths, load_cfg, tokens

# api.ollama.com 301-redirects here; requests downgrades POST->GET on 301, hence the canonical host
ENDPOINT = "https://ollama.com/v1/chat/completions"
ENVFILE = "/root/.or_zai_env"

SYSTEM = (
    "glossary builder for a 19th-century Portuguese history book; one short English "
    "gloss per word (max 4 words); two very different common senses separated by "
    '" / " (max 2 senses); verbs as infinitives; include function words '
    "(de=of, que=that/which); archaic spellings glossed as the modern word's "
    "meaning; proper names -> English form or unchanged. Output STRICT JSON "
    'object {"word":"gloss"} covering every input word, keys exactly as given.'
)


def api_key():
    key = os.environ.get("OLLAMA_API_KEY")
    if not key:
        with open(ENVFILE) as f:
            for line in f:
                if line.startswith("export OLLAMA_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
    return key


def extract_json(text):
    """Pull the first balanced {...} object out of a possibly noisy response."""
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        start = text.find("{", start + 1)
    raise ValueError("no JSON object in response")


def normalize(gloss):
    gloss = re.sub(r"\s+", " ", gloss).strip()
    return gloss[:60]


def chat(model, words, key):
    r = requests.post(ENDPOINT, timeout=600, headers={"Authorization": f"Bearer {key}"}, json={
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Words: " + ", ".join(words)},
        ],
    })
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def translate_batch(words, cfg, key):
    """Translate a batch, returning {word: gloss} for >=90% of keys."""
    for attempt in range(3):
        try:
            model = cfg["model"]
            try:
                content = chat(model, words, key)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 404 and "model" in e.response.text:
                    print(f"model {model} not found, falling back to {cfg['fallback_model']}")
                    cfg["model"] = model = cfg["fallback_model"]
                    content = chat(model, words, key)
            out = json.loads(extract_json(content))
            got = {w: normalize(g) for w, g in out.items() if w in words and isinstance(g, str) and g.strip()}
            if len(got) >= 0.9 * len(words):
                return got
            print(f"batch low coverage {len(got)}/{len(words)}, retry {attempt + 1}")
        except Exception as e:
            print(f"batch error: {e}, retry {attempt + 1}")
        time.sleep(2)
    return {}


def run():
    cfg = load_cfg()
    key = api_key()
    if not key:
        sys.exit("OLLAMA_API_KEY not set")
    ch_path, gl_path = data_paths(cfg)
    with open(ch_path, encoding="utf-8") as f:
        chapters = json.load(f)["chapters"]
    vocab = set()
    for ch in chapters:
        for p in ch["paras"]:
            vocab.update(tokens(p["text"]))
    words = sorted(vocab)
    try:
        with open(gl_path, encoding="utf-8") as f:
            gloss = json.load(f)
    except FileNotFoundError:
        gloss = {}
    todo = [w for w in words if w not in gloss]
    print(f"total unique: {len(words)}, already glossed: {len(words) - len(todo)}")
    bs = cfg["batch_size"]
    for i in range(0, len(todo), bs):
        batch = todo[i:i + bs]
        print(f"batch {i // bs + 1}/{(len(todo) + bs - 1) // bs} ({len(batch)} words)")
        gloss.update(translate_batch(batch, cfg, key))
        with open(gl_path, "w", encoding="utf-8") as f:
            json.dump(gloss, f, ensure_ascii=False, indent=1)
    # solo pass for stragglers
    for w in [w for w in words if w not in gloss]:
        got = translate_batch([w], cfg, key)
        gloss.update(got)
        with open(gl_path, "w", encoding="utf-8") as f:
            json.dump(gloss, f, ensure_ascii=False, indent=1)
    missing = [w for w in words if w not in gloss]
    print(f"coverage: total {len(words)}, glossed {len(words) - len(missing)}, missing {len(missing)}")
    if missing:
        print("missing:", ", ".join(missing[:50]))


def coverage(chapters_path=None, glossary_path=None):
    ch_path, gl_path = data_paths()
    with open(chapters_path or ch_path, encoding="utf-8") as f:
        chapters = json.load(f)["chapters"]
    with open(glossary_path or gl_path, encoding="utf-8") as f:
        gloss = json.load(f)
    vocab = set()
    for ch in chapters:
        for p in ch["paras"]:
            vocab.update(tokens(p["text"]))
    hit = sum(1 for w in vocab if w in gloss)
    return hit, len(vocab)

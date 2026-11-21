import json

from .fetch import load_cfg
from .gloss import coverage

TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#faf7f0;--fg:#2b2722;--muted:#777;--flip:#8a4b2a;--flipbg:#f3e3d4;--line:#ddd6c8}
html[data-dk]{--bg:#1c1a17;--fg:#ddd6c8;--muted:#999;--flip:#e8b98a;--flipbg:#3a2f24;--line:#3a352d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Georgia,'Times New Roman',serif;
font-size:1.15rem;line-height:1.75;touch-action:manipulation}
header{position:sticky;top:0;z-index:1;background:var(--bg);border-bottom:1px solid var(--line);
display:flex;align-items:center;gap:.5rem;padding:.5rem 1rem;flex-wrap:wrap}
header h1{font-size:1rem;font-weight:600;margin:0 auto 0 0}
button{font:inherit;background:none;border:1px solid var(--line);border-radius:.4rem;
color:var(--fg);padding:.15rem .6rem;cursor:pointer}
main{max-width:41rem;margin:0 auto;padding:1rem}
h2{font-size:1.3rem;margin:1.5rem 0 .5rem}
p{margin:0 0 1rem}
.w{cursor:pointer;border-bottom:1px dotted var(--muted)}
.w.f{color:var(--flip);background:var(--flipbg);border-radius:.2rem;
box-shadow:0 1px 0 var(--flip);border-bottom:none}
.x{cursor:default}
footer{max-width:41rem;margin:0 auto 1rem;padding:0 1rem;color:var(--muted);font-size:.8rem}
</style>
</head>
<body>
<header>
<h1>__TITLE__</h1>
<button id="fs-">A−</button><button id="fs+">A+</button>
<button id="dk">◐</button><button id="unflip">unflip all</button>
</header>
<main id="main"></main>
<footer>Fonte: __SOURCE__</footer>
<script>
const DATA = __CHAPTERS__;
const GLOSS = __GLOSSARY__;
const WRE = /[A-Za-zÀ-ÖØ-öø-ÿ']+/g;
const SRE = /(?<=[.!?;:])\s+/;
const main = document.getElementById('main');
function render(){
  for (const ch of DATA.chapters){
    const h = document.createElement('h2'); h.textContent = ch.title; main.appendChild(h);
    for (const p of ch.paras){
      const el = document.createElement(p.t === 'h' ? 'h3' : 'p');
      if (p.t === 'h'){ el.textContent = p.text; }
      else {
        for (const sent of p.text.split(SRE)){
          if (!sent.trim()) continue;
          const s = document.createElement('span'); s.className = 's';
          let last = 0, m;
          WRE.lastIndex = 0;
          while ((m = WRE.exec(sent)) !== null){
            s.appendChild(document.createTextNode(sent.slice(last, m.index)));
            const w = document.createElement('span');
            const lo = m[0].toLowerCase(), g = GLOSS[lo];
            if (g){ w.className = 'w'; w.dataset.o = m[0]; w.dataset.g = g; w.textContent = m[0]; }
            else { w.className = 'w x'; w.textContent = m[0]; }
            s.appendChild(w); last = m.index + m[0].length;
          }
          s.appendChild(document.createTextNode(sent.slice(last)));
          el.appendChild(s); el.appendChild(document.createTextNode(' '));
        }
      }
      main.appendChild(el);
    }
  }
}
main.addEventListener('click', e => {
  const w = e.target.closest('.w');
  if (!w || w.classList.contains('x')) return;
  const toG = !w.classList.contains('f');
  w.textContent = toG ? w.dataset.g : w.dataset.o;
  w.title = toG ? w.dataset.o : w.dataset.g;
  w.classList.toggle('f', toG);
});
main.addEventListener('dblclick', e => {
  const s = e.target.closest('.s');
  if (!s) return;
  const ws = s.querySelectorAll('.w:not(.x)');
  const anyOff = [...ws].some(w => !w.classList.contains('f'));
  ws.forEach(w => {
    w.textContent = anyOff ? w.dataset.g : w.dataset.o;
    w.title = anyOff ? w.dataset.o : w.dataset.g;
    w.classList.toggle('f', anyOff);
  });
});
document.getElementById('unflip').onclick = () =>
  document.querySelectorAll('.w.f').forEach(w => {
    w.textContent = w.dataset.o; w.title = w.dataset.g; w.classList.remove('f');
  });
const fsBtn = d => {
  let fs = parseFloat(localStorage.frFs || '1.15') + d * 0.12;
  fs = Math.min(1.9, Math.max(0.85, fs));
  document.body.style.fontSize = fs + 'rem'; localStorage.frFs = fs;
};
document.getElementById('fs-').onclick = () => fsBtn(-1);
document.getElementById('fs+').onclick = () => fsBtn(1);
const html = document.documentElement;
if (localStorage.frDk === '1') html.setAttribute('data-dk', '');
document.getElementById('dk').onclick = () => {
  const on = html.hasAttribute('data-dk');
  if (on) html.removeAttribute('data-dk'); else html.setAttribute('data-dk', '');
  localStorage.frDk = on ? '0' : '1';
};
let fsInit = localStorage.frFs;
if (fsInit) document.body.style.fontSize = fsInit + 'rem';
addEventListener('beforeunload', () => {
  localStorage.frPos = scrollY / Math.max(1, document.body.scrollHeight - innerHeight);
});
render();
if (localStorage.frPos) scrollTo(0, localStorage.frPos * (document.body.scrollHeight - innerHeight));
</script>
</body>
</html>
"""


def embed(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def run():
    cfg = load_cfg()
    with open("data/chapters.json", encoding="utf-8") as f:
        chapters = json.load(f)
    with open("data/glossary.json", encoding="utf-8") as f:
        glossary = json.load(f)
    hit, total = coverage()
    print(f"coverage: {hit}/{total} ({100 * hit / total:.1f}%)")
    html = (TEMPLATE
            .replace("__TITLE__", f"{cfg['work']} · Manuel Pinheiro Chagas · 1881")
            .replace("__SOURCE__", chapters["chapters"][0]["url"])
            .replace("__CHAPTERS__", embed(chapters))
            .replace("__GLOSSARY__", embed(glossary)))
    import os
    os.makedirs("dist", exist_ok=True)
    with open("dist/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"dist/index.html: {len(html)} bytes")

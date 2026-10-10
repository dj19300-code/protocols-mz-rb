cat > ~/protocols-app/app.py << 'PYEOF'
import sqlite3, os, re
from flask import Flask, request, send_file, abort, jsonify

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "protocols.db")
PDF = os.path.join(BASE, "clinical_protocols")

SPECIALTIES = [
    ("Ревматология", ["артрит","подагра","склероз","волчанк","васкулит","спондил","Шегрен","Бехчет","Стилл","полимиалг","фибромиалг","полиангиит","Гудпасчер","панникулит","остеоартроз","артропат","Фелти","криоглобулин","саркоид"]),
    ("Кардиология", ["гипертенз","стенокард","ИБС","ТЭЛА","митральн","аортальн","клапан","сердц"]),
    ("Пульмонология", ["астм","бронхит","ХОБЛ","легк","плевры","микобактер","обструктивн"]),
    ("Гастроэнтерология", ["пищевод","желудк","кишечник","печен","желчн","поджелудочн","гастродуоден","кишк"]),
    ("Эндокринология", ["диабет","щитовидн","паращитовидн","гипофиз","надпочечник","гонад","ожирен"]),
    ("Нефрология", ["нефролог","почек","почечн"]),
    ("Онкология", ["рак ","мезотелиом","опухол","вилочков"]),
    ("Акушерство", ["родоразреш","беремен","родов"]),
    ("Гематология", ["тромбофил","тромбоэмбол","антифосфолипид"]),
    ("Интенсивная терапия", ["интенсивн","критическ","дистресс","реанимац"]),
    ("Иммунология", ["иммунодефицит"]),
    ("Хирургия", ["кровотечен","вен "]),
]

def detect_specialty(t):
    tl = t.lower()
    for spec, keys in SPECIALTIES:
        for k in keys:
            if k.lower() in tl: return spec
    return "Прочее"

def clean_title(t):
    t = re.sub(r'\.pdf$', '', t, flags=re.I).replace('%20',' ').replace('_',' ')
    t = re.sub(r'\s+', ' ', t).strip()
    m = re.match(r'^([А-ЯA-Z]+\d+)\s+(.+)$', t)
    return (m.group(1), m.group(2)) if m else ("", t)

def highlight(text, q):
    if not q or not text: return ""
    t = re.sub(r'\s+', ' ', text)
    idx = t.lower().find(q.lower())
    if idx < 0: return ""
    s, e = max(0, idx-100), min(len(t), idx+len(q)+200)
    frag = t[s:e]
    frag = re.sub(re.escape(q), lambda m: f"<mark>{m.group(0)}</mark>", frag, flags=re.I)
    return ("…" if s>0 else "") + frag + ("…" if e<len(t) else "")

# ---- Словарь для подсказок (кэш) ----
_WORDS = None
def get_words():
    global _WORDS
    if _WORDS is not None: return _WORDS
    words = set()
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT title FROM protocols")
    for (t,) in c.fetchall():
        for w in re.findall(r'[А-Яа-яЁёA-Za-z]{3,}', t):
            words.add(w.lower())
    c.execute("SELECT full_text FROM protocols")
    counter = {}
    for (txt,) in c.fetchall():
        if not txt: continue
        for w in re.findall(r'[А-Яа-яЁё]{4,}', txt):
            wl = w.lower()
            counter[wl] = counter.get(wl, 0) + 1
    for w, _ in sorted(counter.items(), key=lambda x: -x[1])[:800]:
        words.add(w)
    conn.close()
    _WORDS = sorted(words)
    return _WORDS

def page(body, title="Протоколы МЗ РБ"):
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{{--blue:#0d4d8c;--blue2:#1a6fc4;--teal:#17b8a6;--teal2:#0d9488;--bg:#f5f7fb;--bg2:#fff;--text:#0f172a;--muted:#64748b;--border:#e2e8f0;--shadow:0 1px 3px rgba(0,0,0,.06);--shadow-lg:0 12px 32px rgba(13,77,140,.14);--amber:#f59e0b;--amber-bg:#fffbeb}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0b1220;--bg2:#111a2e;--text:#e6edf7;--muted:#8ea1bd;--border:#1e2a44;--amber-bg:#1f1a08}}}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.55;-webkit-font-smoothing:antialiased;min-height:100vh}}
a{{color:var(--blue2);text-decoration:none;transition:color .15s}}a:hover{{color:var(--teal2)}}
header{{background:linear-gradient(135deg,#052a52 0%,#0d4d8c 40%,#1a6fc4 75%,#17b8a6 130%);color:#fff;padding:40px 20px 66px;position:relative;overflow:hidden}}
header::before{{content:"";position:absolute;top:-160px;right:-140px;width:520px;height:520px;background:radial-gradient(circle,rgba(23,184,166,.4) 0%,transparent 65%);border-radius:50%;animation:pulse 8s ease-in-out infinite}}
header::after{{content:"";position:absolute;bottom:-120px;left:-100px;width:380px;height:380px;background:radial-gradient(circle,rgba(26,111,196,.35) 0%,transparent 70%);border-radius:50%}}
@keyframes pulse{{0%,100%{{transform:scale(1);opacity:.9}}50%{{transform:scale(1.08);opacity:.6}}}}
.wrap{{max-width:1180px;margin:0 auto;position:relative;z-index:1}}
.logo{{font-size:23px;font-weight:800;display:flex;align-items:center;gap:12px;letter-spacing:-.6px}}
.logo .icon{{width:38px;height:38px;background:rgba(255,255,255,.18);border-radius:11px;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(8px)}}
.logo .badge{{background:rgba(255,255,255,.18);padding:6px 13px;border-radius:9px;font-size:12px;font-weight:600;letter-spacing:.4px}}
.sub{{font-size:14.5px;opacity:.88;margin-top:12px;font-weight:500}}
.search-wrap{{position:relative;max-width:720px;margin-top:26px}}
.search{{background:var(--bg2);border-radius:18px;padding:7px;display:flex;box-shadow:var(--shadow-lg);position:relative}}
.search input{{flex:1;padding:16px 22px;font-size:16px;border:none;outline:none;background:transparent;color:var(--text);border-radius:14px;font-family:inherit;font-weight:500}}
.search input::placeholder{{color:var(--muted);font-weight:400}}
.search button{{padding:16px 30px;font-size:15px;font-weight:700;background:linear-gradient(135deg,var(--teal),var(--teal2));color:#fff;border:none;border-radius:13px;cursor:pointer;transition:.2s;display:flex;align-items:center;gap:9px;font-family:inherit}}
.search button:hover{{transform:translateY(-1px);box-shadow:0 8px 20px rgba(23,184,166,.45)}}
.suggest{{position:absolute;top:calc(100% + 6px);left:0;right:0;background:var(--bg2);border-radius:14px;box-shadow:var(--shadow-lg);overflow:hidden;z-index:100;display:none;border:1px solid var(--border)}}
.suggest.open{{display:block}}
.sug-item{{padding:13px 22px;cursor:pointer;font-size:14.5px;font-weight:500;border-bottom:1px solid var(--border);transition:.1s;display:flex;align-items:center;gap:10px}}
.sug-item:last-child{{border-bottom:none}}
.sug-item svg{{width:15px;height:15px;color:var(--muted);flex-shrink:0}}
.sug-item mark{{background:transparent;color:var(--teal2);font-weight:800;padding:0}}
.sug-item:hover,.sug-item.active{{background:linear-gradient(135deg,#e6f0fa,#dbeafe);color:var(--blue)}}
@media(prefers-color-scheme:dark){{.sug-item:hover,.sug-item.active{{background:linear-gradient(135deg,#0d2725,#0f2a3f)}}}}
.container{{max-width:1180px;margin:-40px auto 70px;padding:0 20px;position:relative;z-index:2}}
.bar{{background:var(--bg2);border-radius:16px;padding:16px 24px;box-shadow:var(--shadow);font-size:14px;color:var(--muted);margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;font-weight:500}}
.bar b{{color:var(--text);font-weight:700}}
.bar .reset{{color:var(--blue2);font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:6px}}
.chips{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:26px}}
.chip{{padding:11px 20px;background:var(--bg2);border:1.5px solid var(--border);border-radius:24px;font-size:13.5px;color:var(--text);cursor:pointer;transition:.18s;font-weight:600;display:inline-flex;align-items:center;gap:8px;box-shadow:0 1px 2px rgba(0,0,0,.03)}}
.chip .count{{background:#e8eef7;color:var(--blue);font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:12px;min-width:22px;text-align:center}}
.chip:hover{{border-color:var(--blue2);color:var(--blue2);transform:translateY(-2px)}}
.chip:hover .count{{background:var(--blue2);color:#fff}}
.chip.on{{background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;border-color:transparent;box-shadow:0 6px 18px rgba(13,77,140,.3)}}
.chip.on .count{{background:rgba(255,255,255,.22);color:#fff}}
@media(prefers-color-scheme:dark){{.chip .count{{background:#1e2a44;color:#8fb8e8}}}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px;align-items:stretch}}
.card{{background:var(--bg2);border-radius:16px;padding:24px;box-shadow:var(--shadow);transition:.22s cubic-bezier(.4,0,.2,1);border:1px solid var(--border);position:relative;overflow:hidden;display:flex;flex-direction:column;min-height:230px}}
.card::before{{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg,var(--blue2),var(--teal));transition:.3s}}
.card:hover{{box-shadow:var(--shadow-lg);transform:translateY(-4px);border-color:transparent}}
.card:hover::before{{width:6px}}
.tags{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}}
.tag{{display:inline-block;background:linear-gradient(135deg,#e6faf7,#d1fae5);color:var(--teal2);font-size:11px;font-weight:700;padding:5px 11px;border-radius:7px;letter-spacing:.4px;text-transform:uppercase}}
.tag.code{{background:#e6f0fa;color:var(--blue)}}
@media(prefers-color-scheme:dark){{.tag{{background:#0d2725;color:#5eead4}}.tag.code{{background:#1a2a44;color:#8fb8e8}}}}
.card h3{{font-size:16px;font-weight:600;line-height:1.45;margin-bottom:14px;flex:1;letter-spacing:-.2px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
.card h3 a{{color:var(--text)}}.card h3 a:hover{{color:var(--blue2)}}
.meta{{font-size:13px;color:var(--muted);display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding-top:14px;border-top:1px solid var(--border);margin-top:auto}}
.meta .pages{{font-weight:600}}
.meta .m-link{{color:var(--blue2);font-weight:600;display:inline-flex;align-items:center;gap:5px;font-size:13px}}
.meta .m-link:hover{{color:var(--teal2)}}
.meta svg{{width:14px;height:14px}}
.snippet{{margin-top:14px;padding:12px 16px;background:var(--amber-bg);border-left:3px solid var(--amber);border-radius:8px;font-size:13px;line-height:1.55}}
mark{{background:#fde68a;color:#78350f;padding:1px 4px;border-radius:4px;font-weight:600}}
@media(prefers-color-scheme:dark){{mark{{background:#78350f;color:#fde68a}}}}
.empty{{text-align:center;padding:90px 20px;color:var(--muted);background:var(--bg2);border-radius:16px;border:1px dashed var(--border);font-size:15px;font-weight:500}}
.empty svg{{width:64px;height:64px;margin:0 auto 18px;display:block;opacity:.3}}
.detail-head{{background:var(--bg2);padding:32px 34px;border-radius:18px;margin-top:24px;box-shadow:var(--shadow);border:1px solid var(--border)}}
.detail-head h1{{font-size:26px;line-height:1.35;color:var(--text);margin:12px 0 16px;letter-spacing:-.5px;font-weight:700}}
.actions{{display:flex;gap:12px;margin-top:20px;flex-wrap:wrap}}
.btn{{display:inline-flex;align-items:center;gap:9px;padding:13px 24px;border-radius:12px;font-weight:600;font-size:14.5px;transition:.18s;font-family:inherit;border:none;cursor:pointer}}
.btn.primary{{background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;box-shadow:0 6px 18px rgba(13,77,140,.3)}}
.btn.primary:hover{{transform:translateY(-2px);color:#fff}}
.btn.ghost{{background:var(--bg2);color:var(--blue2);border:1.5px solid var(--blue2)}}
.btn.ghost:hover{{background:var(--blue2);color:#fff;transform:translateY(-2px)}}
.btn svg{{width:17px;height:17px}}
.text-body{{background:var(--bg2);border-radius:16px;padding:40px 46px;margin-top:20px;line-height:1.85;font-size:15.5px;white-space:pre-wrap;font-family:Georgia,serif;box-shadow:var(--shadow);border:1px solid var(--border)}}
.back{{display:inline-flex;align-items:center;gap:8px;margin:24px 0 0;font-size:14px;color:var(--blue2);font-weight:600}}
.back svg{{width:15px;height:15px}}
.to-top{{position:fixed;bottom:28px;right:28px;width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 8px 24px rgba(13,77,140,.4);opacity:0;pointer-events:none;transition:.25s;z-index:100}}
.to-top.show{{opacity:1;pointer-events:auto}}
.to-top:hover{{background:linear-gradient(135deg,var(--teal),var(--teal2));transform:translateY(-4px)}}
@media(max-width:700px){{header{{padding:28px 18px 52px}}.logo{{font-size:19px}}.search input{{padding:14px 16px;font-size:15px}}.search button{{padding:14px 20px;font-size:14px}}.text-body{{padding:22px 24px;font-size:14.5px}}.detail-head{{padding:22px}}.detail-head h1{{font-size:21px}}.grid{{gap:14px;grid-template-columns:1fr}}.card{{padding:20px;min-height:auto}}.container{{padding:0 16px}}.chip{{padding:9px 15px;font-size:12.5px}}}}
</style></head><body>{body}
<a href="#" class="to-top" id="toTop"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="22" height="22"><polyline points="18 15 12 9 6 15"/></svg></a>
<script>
const btn=document.getElementById('toTop');
window.addEventListener('scroll',()=>{{btn.classList.toggle('show',window.scrollY>400)}});
btn.addEventListener('click',e=>{{e.preventDefault();window.scrollTo({{top:0,behavior:'smooth'}})}});

// === Автодополнение ===
const inp=document.querySelector('input[name="q"]');
const sug=document.getElementById('suggest');
let items=[],idx=-1,tmr=null,ctrl=null;

function render(q){{
  if(!items.length){{sug.classList.remove('open');return}}
  sug.innerHTML=items.map((w,i)=>{{
    const hi=w.replace(new RegExp('^('+q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&')+')','i'),'<mark>$1</mark>');
    return `<div class="sug-item${{i===idx?' active':''}}" data-w="${{w}}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      ${{hi}}</div>`;
  }}).join('');
  sug.classList.add('open');
  sug.querySelectorAll('.sug-item').forEach(el=>{{
    el.addEventListener('mousedown',e=>{{e.preventDefault();pick(el.dataset.w)}});
  }});
}}
function pick(w){{
  inp.value=w;sug.classList.remove('open');
  inp.form.submit();
}}
inp.addEventListener('input',()=>{{
  const q=inp.value.trim();
  clearTimeout(tmr);
  if(ctrl) ctrl.abort();
  if(q.length<2){{items=[];idx=-1;render(q);return}}
  tmr=setTimeout(()=>{{
    ctrl=new AbortController();
    fetch('/api/suggest?q='+encodeURIComponent(q),{{signal:ctrl.signal}})
      .then(r=>r.json()).then(d=>{{items=d.items||[];idx=-1;render(q)}})
      .catch(()=>{{}});
  }},150);
}});
inp.addEventListener('keydown',e=>{{
  if(!sug.classList.contains('open')) return;
  if(e.key==='ArrowDown'){{e.preventDefault();idx=Math.min(idx+1,items.length-1);render(inp.value.trim())}}
  else if(e.key==='ArrowUp'){{e.preventDefault();idx=Math.max(idx-1,-1);render(inp.value.trim())}}
  else if(e.key==='Enter'&&idx>=0){{e.preventDefault();pick(items[idx])}}
  else if(e.key==='Escape'){{sug.classList.remove('open');idx=-1}}
}});
document.addEventListener('click',e=>{{if(!e.target.closest('.search-wrap'))sug.classList.remove('open')}});
</script>
</body></html>"""

IC_PDF='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>'
IC_DOWN='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'
IC_SEARCH='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="18" height="18"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
IC_BACK='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>'
IC_X='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
IC_EMPTY='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/></svg>'
IC_LOGO='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="22" height="22"><path d="M9 12h6m-3-3v6m-7 3V6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2z"/></svg>'

@app.route("/api/suggest")
def api_suggest():
    q = request.args.get("q","").strip().lower()
    if len(q) < 2: return jsonify({"items": []})
    words = get_words()
    starts = [w for w in words if w.startswith(q)]
    starts.sort(key=lambda w: (len(w), w))
    return jsonify({"items": starts[:10]})

@app.route("/")
def index():
    q = request.args.get("q","").strip()
    spec_filter = request.args.get("spec","").strip()
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM protocols"); total = c.fetchone()[0]
    c.execute("SELECT filename FROM protocols")
    spec_counts = {}
    for (f,) in c.fetchall():
        _, name = clean_title(f)
        s = detect_specialty(name)
        spec_counts[s] = spec_counts.get(s, 0) + 1
    spec_counts = dict(sorted(spec_counts.items(), key=lambda x:(-x[1], x[0])))
    if q:
        try:
            c.execute("SELECT p.id,p.filename,p.full_text,p.page_count FROM protocols_fts f JOIN protocols p ON p.id=f.rowid WHERE protocols_fts MATCH ? ORDER BY rank LIMIT 200", (q+"*",))
            rows = c.fetchall()
        except Exception:
            c.execute("SELECT id,filename,full_text,page_count FROM protocols WHERE LOWER(title) LIKE ? OR LOWER(full_text) LIKE ? LIMIT 200", (f"%{q.lower()}%",f"%{q.lower()}%"))
            rows = c.fetchall()
    else:
        c.execute("SELECT id,filename,full_text,page_count FROM protocols ORDER BY title LIMIT 500")
        rows = c.fetchall()
    conn.close()
    cards = []
    for pid, fname, full_text, pages in rows:
        code, name = clean_title(fname)
        spec = detect_specialty(name)
        if spec_filter and spec != spec_filter: continue
        snip = highlight(full_text or "", q) if q else ""
        tag_code = f'<span class="tag code">{code}</span>' if code else ''
        cards.append(f'''<div class="card">
        <div class="tags"><span class="tag">{spec}</span>{tag_code}</div>
        <h3><a href="/p/{pid}">{name}</a></h3>
        <div class="meta"><span class="pages">{pages} стр.</span>
          <a href="/pdf/{pid}" target="_blank" class="m-link">{IC_PDF}PDF</a>
          <a href="/pdf/{pid}?download=1" class="m-link">{IC_DOWN}Скачать</a></div>
        {f'<div class="snippet">{snip}</div>' if snip else ''}</div>''')
    chips = f'<a href="/" class="chip{" on" if not spec_filter and not q else ""}">Все <span class="count">{total}</span></a>'
    for s, n in spec_counts.items():
        if n == 0: continue
        on = " on" if spec_filter == s else ""
        qs = f"&q={q}" if q else ""
        chips += f'<a href="/?spec={s}{qs}" class="chip{on}">{s} <span class="count">{n}</span></a>'
    reset = f'<a href="/" class="reset">{IC_X} Сбросить</a>' if (q or spec_filter) else ''
    stats = f"Найдено <b>{len(cards)}</b> из {total}" if q else f"Показано <b>{len(cards)}</b> из {total}"
    cards_html = '<div class="grid">' + "".join(cards) + "</div>" if cards else f'<div class="empty">{IC_EMPTY}<div>Ничего не найдено</div><div style="font-size:13px;margin-top:8px;font-weight:400">Попробуйте другое слово или сбросьте фильтр</div></div>'
    body = f'''
    <header><div class="wrap">
      <div class="logo"><span class="icon">{IC_LOGO}</span>Клинические протоколы <span class="badge">МЗ РБ</span></div>
      <div class="sub">{total} протоколов · умный поиск с подсказками</div>
      <div class="search-wrap">
        <form class="search" method="get" action="/" autocomplete="off">
          <input name="q" value="{q}" placeholder="Начните вводить: диабет, артрит, метотрексат..." autofocus>
          {f'<input type="hidden" name="spec" value="{spec_filter}">' if spec_filter else ''}
          <button type="submit">{IC_SEARCH} Найти</button>
        </form>
        <div class="suggest" id="suggest"></div>
      </div>
    </div></header>
    <div class="container">
      <div class="bar"><span>{stats}</span>{reset}</div>
      <div class="chips">{chips}</div>
      {cards_html}
    </div>'''
    return page(body)

@app.route("/p/<int:pid>")
def protocol(pid):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT filename,full_text,page_count FROM protocols WHERE id=?", (pid,))
    r = c.fetchone(); conn.close()
    if not r: abort(404)
    fname, full_text, pages = r
    code, name = clean_title(fname)
    spec = detect_specialty(name)
    tag_code = f'<span class="tag code">{code}</span>' if code else ''
    body = f'''
    <div class="container">
      <a class="back" href="/">{IC_BACK} Все протоколы</a>
      <div class="detail-head">
        <div class="tags"><span class="tag">{spec}</span>{tag_code}</div>
        <h1>{name}</h1>
        <div class="meta" style="border:none;padding:0"><span class="pages">{pages} страниц</span></div>
        <div class="actions">
          <a class="btn primary" href="/pdf/{pid}" target="_blank">{IC_PDF} Открыть PDF</a>
          <a class="btn ghost" href="/pdf/{pid}?download=1">{IC_DOWN} Скачать</a>
        </div>
      </div>
      <div class="text-body">{full_text or "Текст не извлечён."}</div>
    </div>'''
    return page(body, title=name)

@app.route("/pdf/<int:pid>")
def pdf(pid):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT filename FROM protocols WHERE id=?", (pid,))
    r = c.fetchone(); conn.close()
    if not r: abort(404)
    path = os.path.join(PDF, r[0])
    if not os.path.exists(path): abort(404)
    resp = send_file(path, as_attachment=(request.args.get("download")=="1"), download_name=r[0])
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp

if __name__ == "__main__":
    print("="*55)
    print("🩺  Протоколы МЗ РБ — v4 (автодополнение)")
    print("Локально: http://localhost:5000")
    print("="*55)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
PYEOF
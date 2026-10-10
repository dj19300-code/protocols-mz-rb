import sqlite3, os, re
from flask import Flask, request, send_file

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "protocols.db")
PDF = os.path.join(BASE, "clinical_protocols")

# --- Специальности (по ключевым словам в названии) ---
SPECIALTIES = [
    ("Ревматология", ["артрит","подагра","склероз","волчанк","васкулит","спондил","Шегрен","Бехчет","Стилл","полимиалг","фибромиалг","полиангиит","Гудпасчер","панникулит","остеоартроз","артропат","Фелти","криоглобулин","саркоид"]),
    ("Кардиология", ["гипертенз","стенокард","ИБС","ТЭЛА","митральн","аортальн","клапан","сердц"]),
    ("Пульмонология", ["астм","бронхит","ХОБЛ","легк","плевры","микобактер","обструктивн"]),
    ("Гастроэнтерология", ["пищевод","желудк","кишечник","печен","желчн","поджелудочн","гастродуоден","кишк"]),
    ("Эндокринология", ["диабет","щитовидн","паращитовидн","гипофиз","надпочечник","гонад","ожирен"]),
    ("Нефрология", ["нефролог","почек","почечн"]),
    ("Онкология", ["рак","мезотелиом","опухол","вилочков"]),
    ("Акушерство", ["родоразреш","беремен","родов"]),
    ("Гематология", ["тромбофил","тромбоэмбол","антифосфолипид"]),
    ("Интенсивная терапия", ["интенсивн","критическ","дистресс","реанимац"]),
    ("Иммунология", ["иммунодефицит"]),
    ("Хирургия", ["кровотечен","вен"]),
]

def detect_specialty(title):
    tl = title.lower()
    for spec, keys in SPECIALTIES:
        for k in keys:
            if k.lower() in tl:
                return spec
    return "Прочее"

def clean_title(t):
    # Убираем расширение и %20, чистим
    t = re.sub(r'\.pdf$', '', t, flags=re.I)
    t = t.replace('%20',' ').replace('_',' ')
    t = re.sub(r'\s+', ' ', t).strip()
    # Разделяем код (КП11) и название
    m = re.match(r'^([А-ЯA-Z]+\d+)\s+(.+)$', t)
    if m:
        return m.group(1), m.group(2)
    return "", t

def highlight(text, query, maxlen=280):
    if not query or not text: return ""
    t = text.replace("\n"," ")
    # ищем регистронезависимо
    idx = t.lower().find(query.lower())
    if idx < 0: return ""
    start = max(0, idx-80)
    end = min(len(t), idx+len(query)+200)
    frag = t[start:end]
    # подсветка
    pat = re.compile(re.escape(query), re.IGNORECASE)
    frag = pat.sub(lambda m: f"<mark>{m.group(0)}</mark>", frag)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(t) else ""
    return prefix + frag + suffix

def page(body, title="Протоколы МЗ РБ"):
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{--blue:#0d4d8c;--blue2:#1a6fc4;--teal:#17b8a6;--bg:#f7fafc;--text:#1a202c;--muted:#64748b;--border:#e2e8f0}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.55;-webkit-font-smoothing:antialiased}}
a{{color:var(--blue);text-decoration:none}}
a:hover{{text-decoration:underline}}
header{{background:linear-gradient(135deg,#073a6b 0%,#0d4d8c 50%,#1a6fc4 100%);color:#fff;padding:36px 20px 52px;position:relative;overflow:hidden}}
header::before{{content:"";position:absolute;top:-140px;right:-120px;width:460px;height:460px;background:radial-gradient(circle,rgba(23,184,166,.32) 0%,transparent 70%);border-radius:50%}}
.wrap{{max-width:1100px;margin:0 auto;position:relative;z-index:1;padding:0 4px}}
.logo{{font-size:22px;font-weight:700;display:flex;align-items:center;gap:10px;letter-spacing:-.5px}}
.logo span{{background:rgba(255,255,255,.16);padding:5px 11px;border-radius:8px;font-size:12px;font-weight:500}}
.sub{{font-size:14px;opacity:.85;margin-top:8px}}
.search{{background:#fff;border-radius:14px;padding:6px;margin-top:22px;display:flex;box-shadow:0 12px 34px rgba(0,0,0,.18);max-width:680px}}
.search input{{flex:1;padding:14px 18px;font-size:16px;border:none;outline:none;background:transparent;color:#1a202c;border-radius:10px}}
.search button{{padding:14px 26px;font-size:15px;font-weight:600;background:linear-gradient(135deg,var(--teal),#0d9488);color:#fff;border:none;border-radius:10px;cursor:pointer;transition:.15s}}
.search button:hover{{filter:brightness(1.08)}}
.container{{max-width:1100px;margin:-32px auto 40px;padding:0 20px;position:relative}}
.bar{{background:#fff;border-radius:12px;padding:14px 20px;box-shadow:0 2px 10px rgba(0,0,0,.05);font-size:14px;color:var(--muted);margin-bottom:18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}}
.chip{{padding:7px 14px;background:#fff;border:1px solid var(--border);border-radius:20px;font-size:13px;color:var(--muted);cursor:pointer;transition:.15s}}
.chip:hover{{border-color:var(--blue);color:var(--blue)}}
.chip.on{{background:var(--blue);color:#fff;border-color:var(--blue)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:16px}}
.card{{background:#fff;border-radius:14px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.06);transition:.18s;border:1px solid var(--border);position:relative;overflow:hidden;display:flex;flex-direction:column}}
.card:hover{{box-shadow:0 10px 26px rgba(13,77,140,.13);transform:translateY(-2px);border-color:#b8d4ee}}
.card::before{{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg,var(--blue),var(--teal))}}
.tag{{display:inline-block;background:#e6f0fa;color:var(--blue);font-size:11px;font-weight:700;padding:3px 9px;border-radius:5px;letter-spacing:.4px;margin-bottom:9px;align-self:flex-start}}
.tag.spec{{background:#e6faf7;color:#0d9488}}
.card h3{{font-size:16px;font-weight:600;line-height:1.4;margin-bottom:10px;flex:1}}
.card h3 a{{color:var(--text)}}
.card h3 a:hover{{color:var(--blue);text-decoration:none}}
.meta{{font-size:13px;color:var(--muted);display:flex;gap:14px;align-items:center;flex-wrap:wrap}}
.meta a{{color:var(--blue);font-weight:500}}
.snippet{{margin-top:12px;padding:10px 14px;background:#fffbeb;border-left:3px solid #f59e0b;border-radius:6px;font-size:13px;color:#57534e;line-height:1.5}}
mark{{background:#fde68a;padding:1px 3px;border-radius:3px;font-weight:600}}
.empty{{text-align:center;padding:70px 20px;color:var(--muted);background:#fff;border-radius:14px;border:1px dashed var(--border)}}
.detail-head{{background:#fff;padding:26px 28px;border-radius:14px;margin-top:24px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.detail-head h1{{font-size:24px;line-height:1.35;color:var(--blue);margin:6px 0 12px}}
.actions{{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}}
.btn{{display:inline-flex;align-items:center;gap:8px;padding:11px 20px;border-radius:10px;font-weight:600;font-size:14px;text-decoration:none!important}}
.btn.primary{{background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff}}
.btn.ghost{{background:#fff;color:var(--blue);border:1.5px solid var(--blue)}}
.btn:hover{{opacity:.92}}
.text-body{{background:#fff;border-radius:14px;padding:32px 40px;margin-top:16px;line-height:1.75;font-size:15px;white-space:pre-wrap;font-family:Georgia,serif;box-shadow:0 1px 3px rgba(0,0,0,.06);border:1px solid var(--border)}}
.back{{display:inline-block;margin:22px 0 0;font-size:14px;color:var(--blue)}}
@media(max-width:600px){{header{{padding:24px 16px 44px}}.logo{{font-size:18px}}.text-body{{padding:20px}}.detail-head{{padding:18px}}}}
</style></head><body>{body}</body></html>"""

@app.route("/")
def index():
    q = request.args.get("q","").strip()
    spec_filter = request.args.get("spec","").strip()
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM protocols"); total = c.fetchone()[0]

    # Получаем все названия для подсчёта категорий
    c.execute("SELECT filename FROM protocols")
    all_files = [r[0] for r in c.fetchall()]
    spec_counts = {}
    for f in all_files:
        _, name = clean_title(f)
        s = detect_specialty(name)
        spec_counts[s] = spec_counts.get(s, 0) + 1
    spec_counts = dict(sorted(spec_counts.items(), key=lambda x:(-x[1], x[0])))

    # Поиск
    if q:
        # регистронезависимый поиск по названию + полному тексту
        c.execute("""
            SELECT id, filename, full_text, page_count FROM protocols
            WHERE LOWER(title) LIKE ? OR LOWER(full_text) LIKE ?
            LIMIT 200
        """, (f"%{q.lower()}%", f"%{q.lower()}%"))
    else:
        c.execute("SELECT id, filename, full_text, page_count FROM protocols ORDER BY title LIMIT 500")
    rows = c.fetchall(); conn.close()

    cards = []
    for pid, fname, full_text, pages in rows:
        code, name = clean_title(fname)
        spec = detect_specialty(name)
        if spec_filter and spec != spec_filter:
            continue
        snip = highlight(full_text or "", q) if q else ""
        card = f'''<div class="card">
            <span class="tag spec">{spec}</span>
            {f'<span class="tag">{code}</span>' if code else ''}
            <h3><a href="/p/{pid}">{name}</a></h3>
            <div class="meta"><span>{pages} стр.</span>
            <a href="/pdf/{pid}" target="_blank">📄 PDF</a>
            <a href="/pdf/{pid}?download=1">⬇️ Скачать</a></div>
            {f'<div class="snippet">{snip}</div>' if snip else ''}
        </div>'''
        cards.append(card)

    # Чипы категорий
    chips_html = f'<a href="/" class="chip {"on" if not spec_filter else ""}">Все ({total})</a>'
    for s, n in spec_counts.items():
        if n == 0: continue
        on = " on" if spec_filter == s else ""
        chips_html += f'<a href="/?spec={s}{f"&q={q}" if q else ""}" class="chip{on}">{s} ({n})</a>'

    if not cards:
        cards_html = '<div class="empty">Ничего не найдено.<br><span style="font-size:13px">Попробуйте другое слово или сбросьте фильтр.</span></div>'
    else:
        cards_html = '<div class="grid">' + "".join(cards) + "</div>"

    body = f'''
    <header><div class="wrap">
      <div class="logo">🩺 Клинические протоколы <span>МЗ РБ</span></div>
      <div class="sub">{total} протоколов в базе · поиск по всему тексту</div>
      <form class="search" method="get" action="/">
        <input name="q" value="{q}" placeholder="Поиск: болезнь, симптом, лекарство, код МКБ...">
        {f'<input type="hidden" name="spec" value="{spec_filter}">' if spec_filter else ''}
        <button>Найти</button>
      </form>
    </div></header>
    <div class="container">
      <div class="bar">
        <span>{f"Найдено: <b>{len(cards)}</b> из {total}" if q else f"Показано: <b>{len(cards)}</b> из {total}"}</span>
        {f'<a href="/">✕ Сбросить фильтр</a>' if (q or spec_filter) else ''}
      </div>
      <div class="chips">{chips_html}</div>
      {cards_html}
    </div>'''
    return page(body)

@app.route("/p/<int:pid>")
def protocol(pid):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT filename, full_text, page_count FROM protocols WHERE id=?", (pid,))
    r = c.fetchone(); conn.close()
    if not r: return "Не найдено", 404
    fname, full_text, pages = r
    code, name = clean_title(fname)
    spec = detect_specialty(name)
    body = f'''
    <div class="container">
      <a class="back" href="/">← Все протоколы</a>
      <div class="detail-head">
        <span class="tag spec">{spec}</span>
        {f'<span class="tag">{code}</span>' if code else ''}
        <h1>{name}</h1>
        <div class="meta"><span>{pages} страниц</span></div>
        <div class="actions">
          <a class="btn primary" href="/pdf/{pid}" target="_blank">📄 Открыть PDF</a>
          <a class="btn ghost" href="/pdf/{pid}?download=1">⬇️ Скачать</a>
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
    if not r: return "Не найдено", 404
    path = os.path.join(PDF, r[0])
    if not os.path.exists(path): return f"Файл не найден: {r[0]}", 404
    return send_file(path, as_attachment=(request.args.get("download")=="1"), download_name=r[0])

if __name__ == "__main__":
    print("="*55)
    print("🩺  Протоколы МЗ РБ")
    print("Сайт:    http://localhost:5000")
    print("Телефон: http://172.30.95.26:5000")
    print("="*55)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

import sqlite3, os
from flask import Flask, request, send_file
app = Flask(__name__)
DB = os.path.expanduser("~/protocols-app/protocols.db")
PDF = os.path.expanduser("~/protocols-app/clinical_protocols")

def page(t, b):
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{t}</title>
<style>
body{{font-family:-apple-system,sans-serif;max-width:960px;margin:0 auto;padding:16px;background:#f0f4f8}}
.top{{background:linear-gradient(135deg,#073a6b,#1a6fc4);color:#fff;padding:24px;border-radius:16px;margin-bottom:16px}}
.top h1{{margin:0;font-size:22px}}.top p{{margin:6px 0 0;opacity:.85;font-size:14px}}
form{{display:flex;gap:8px;margin:16px 0}}
input{{flex:1;padding:14px;font-size:16px;border:1px solid #cbd5e0;border-radius:10px}}
button{{padding:14px 28px;font-size:16px;font-weight:600;background:#0d4d8c;color:#fff;border:none;border-radius:10px;cursor:pointer}}
.card{{background:#fff;padding:16px 20px;margin:8px 0;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.07);border-left:4px solid #0d4d8c}}
.card a{{color:#0d4d8c;text-decoration:none;font-size:16px;font-weight:600}}
.meta{{font-size:13px;color:#718096;margin-top:6px}}.meta a{{font-weight:400;margin-right:10px}}
pre{{white-space:pre-wrap;background:#fff;padding:20px;border-radius:12px;font-family:Georgia,serif;font-size:14px;line-height:1.6}}
.btn{{display:inline-block;padding:10px 20px;background:#0d4d8c;color:#fff!important;border-radius:10px;text-decoration:none!important;font-weight:600;margin:0 8px 14px 0}}
</style></head><body>{b}</body></html>"""

@app.route("/")
def i():
    q = request.args.get("q","").strip()
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM protocols"); n = c.fetchone()[0]
    if q:
        c.execute("SELECT id,title,page_count FROM protocols WHERE title LIKE ? OR full_text LIKE ? LIMIT 200",(f"%{q}%",f"%{q}%"))
    else:
        c.execute("SELECT id,title,page_count FROM protocols ORDER BY title LIMIT 500")
    rows = c.fetchall(); conn.close()
    cards = "".join(f'<div class="card"><a href="/p/{i}">{t}</a><div class="meta">{p} стр. · <a href="/pdf/{i}">📄 PDF</a> · <a href="/pdf/{i}?download=1">⬇️</a></div></div>' for i,t,p in rows) or "<p>Ничего не найдено</p>"
    return page("Протоколы", f'<div class="top"><h1>🩺 Протоколы МЗ РБ</h1><p>{n} документов</p></div><form method="get"><input name="q" value="{q}" placeholder="Поиск..."><button>Найти</button></form>{cards}')

@app.route("/p/<int:i>")
def p(i):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT title,full_text FROM protocols WHERE id=?",(i,)); r = c.fetchone(); conn.close()
    if not r: return "404",404
    return page(r[0], f'<div class="top"><h1>{r[0]}</h1></div><a href="/">← Назад</a><br><br><a class="btn" href="/pdf/{i}">📄 Открыть PDF</a><a class="btn" href="/pdf/{i}?download=1">⬇️ Скачать</a><pre>{r[1]}</pre>')

@app.route("/pdf/<int:i>")
def pdf(i):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT filename FROM protocols WHERE id=?",(i,)); r = c.fetchone(); conn.close()
    if not r: return "404",404
    f = os.path.join(PDF, r[0])
    if not os.path.exists(f): return "404",404
    return send_file(f, as_attachment=(request.args.get("download")=="1"), download_name=r[0])

if __name__ == "__main__":
    print("Сайт: http://localhost:5000")
    import os as _os
    app.run(host="0.0.0.0", port=int(_os.environ.get("PORT", 5000)))

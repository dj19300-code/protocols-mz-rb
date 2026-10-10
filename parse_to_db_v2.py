#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, sqlite3, pdfplumber

PDF_DIR = "/home/bazzetzopka/clinical_protocols"
DB_PATH = "/home/bazzetzopka/protocols.db"

def clean_filename(name):
    name = re.sub(r'\.pdf$', '', name, flags=re.IGNORECASE)
    return name.replace('%20', ' ').replace('_', ' ').strip()

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS protocols")
    c.execute("DROP TABLE IF EXISTS protocols_fts")
    c.execute('''CREATE TABLE protocols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT UNIQUE, title TEXT,
        full_text TEXT, page_count INTEGER)''')
    c.execute('''CREATE VIRTUAL TABLE protocols_fts USING fts5(
        title, full_text, content='protocols', content_rowid='id')''')
    c.execute('''CREATE TRIGGER protocols_ai AFTER INSERT ON protocols BEGIN
        INSERT INTO protocols_fts(rowid, title, full_text)
        VALUES (new.id, new.title, new.full_text); END''')
    conn.commit()

    files = sorted([f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')])
    print(f"Найдено PDF: {len(files)}\n")
    added = 0
    for i, filename in enumerate(files, 1):
        path = os.path.join(PDF_DIR, filename)
        try:
            with pdfplumber.open(path) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages)
                pages = len(pdf.pages)
        except Exception as e:
            print(f"[{i}] SKIP {filename}: {e}"); continue
        if len(text.strip()) < 100:
            print(f"[{i}] SKIP {filename}: мало текста"); continue
        title = clean_filename(filename)
        c.execute("INSERT OR IGNORE INTO protocols (filename,title,full_text,page_count) VALUES (?,?,?,?)",
                  (filename, title, text, pages))
        added += 1
        if i % 10 == 0 or i == len(files):
            print(f"  Прогресс: {i}/{len(files)} | в базе: {added}")
    conn.commit()
    c.execute("SELECT COUNT(*) FROM protocols")
    print(f"\nГотово! Всего в базе: {c.fetchone()[0]}")
    conn.close()

if __name__ == "__main__":
    main()

import sqlite3
import json

conn = sqlite3.connect("universidad.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("==================================================")
print("           INSPECTOR DE BASE DE DATOS             ")
print("==================================================")

tablas = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
print(f"Tablas encontradas: {tablas}\n")

for tabla in tablas:
    if tabla == "sqlite_sequence":
        continue
    count = cursor.execute(f"SELECT COUNT(*) FROM {tabla};").fetchone()[0]
    print(f"--- TABLA: '{tabla}' ({count} registros) ---")
    rows = cursor.execute(f"SELECT * FROM {tabla} LIMIT 3;").fetchall()
    for row in rows:
        print("  ", dict(row))
    print()

conn.close()

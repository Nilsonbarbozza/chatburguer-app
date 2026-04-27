import sqlite3
import os

def inspect():
    db_path = 'data/vector_db/chroma.sqlite3'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    
    for table in tables:
        print(f"\n--- TABELA: {table} ---")
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        for c in cols:
            print(f"Col: {c[1]} ({c[2]})")

    conn.close()

if __name__ == '__main__':
    inspect()

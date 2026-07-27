import os
import sqlite3
from pathlib import Path

db_path = Path.home() / ".vectora" / "data" / "backend.db"
if not db_path.exists():
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", [t[0] for t in tables])
    for table in [t[0] for t in tables]:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        print(f"Columns in {table}:", [c[1] for c in columns])
    conn.close()

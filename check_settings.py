import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('supermarket.db')
cursor = conn.execute("SELECT key, value FROM settings WHERE key LIKE 'mail_%'")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

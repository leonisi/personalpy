import sqlite3
conn = sqlite3.connect("finance.db")
cursor = conn.cursor()
cursor.execute("ALTER TABLE users ADD COLUMN token TEXT;")
conn.commit()
conn.close()
print("Token column added to users table.")

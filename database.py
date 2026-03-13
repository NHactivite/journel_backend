import sqlite3

conn = sqlite3.connect("journal.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
    CREATE TABLE IF NOT EXISTS journals (
        id          TEXT PRIMARY KEY,
        user_id     TEXT NOT NULL,
        ambience    TEXT NOT NULL,
        text        TEXT NOT NULL,
        created_at  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS journal_analysis (
        id          TEXT PRIMARY KEY,
        journal_id  TEXT NOT NULL UNIQUE,
        emotion     TEXT,
        keywords    TEXT,          -- JSON array string
        summary     TEXT,
        analyzed_at TEXT NOT NULL,
        FOREIGN KEY (journal_id) REFERENCES journals(id)
    );
""")
conn.commit()

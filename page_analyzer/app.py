import os
from flask import Flask
from dotenv import load_dotenv
import psycopg2
import sqlite3

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

DATABASE_URL = os.getenv('DATABASE_URL')

SCHEMA = '''
DROP TABLE IF EXISTS url_checks;
DROP TABLE IF EXISTS urls;

CREATE TABLE urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS urls_name_idx ON urls (name);

CREATE TABLE url_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_id INTEGER REFERENCES urls (id),
    status_code INTEGER,
    h1 VARCHAR(255),
    title VARCHAR(255),
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
'''

POSTGRES_SCHEMA = '''
DROP TABLE IF EXISTS url_checks;
DROP TABLE IF EXISTS urls;

CREATE TABLE urls (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS urls_name_idx ON urls (name);

CREATE TABLE url_checks (
    id SERIAL PRIMARY KEY,
    url_id INTEGER REFERENCES urls (id),
    status_code INTEGER,
    h1 VARCHAR(255),
    title VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''


def get_connection():
    """Get database connection."""
    if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
        return psycopg2.connect(DATABASE_URL)
    sqlite_path = os.getenv('SQLITE_PATH', 'database.sqlite')
    return sqlite3.connect(sqlite_path)


def init_db():
    """Initialize database schema."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        try:
            if isinstance(conn, sqlite3.Connection):
                cursor.executescript(SCHEMA)
            else:
                cursor.execute(POSTGRES_SCHEMA)
            conn.commit()
        finally:
            cursor.close()
    finally:
        conn.close()


if DATABASE_URL:  # Инициализация только если указан URL базы данных
    init_db()

from page_analyzer import routes  # noqa: E402, F401

if __name__ == '__main__':
    app.run()


# ... existing code...

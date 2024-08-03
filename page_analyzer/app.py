from flask import Flask
import os
from dotenv import load_dotenv
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

DATABASE_URL = os.getenv('DATABASE_URL')


def get_connection():
    if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
        return psycopg2.connect(DATABASE_URL)
    else:
        sqlite_path = os.getenv('SQLITE_PATH', 'database.sqlite')
        return sqlite3.connect(sqlite_path)


def get_cursor():
    conn = get_connection()
    if isinstance(conn, psycopg2.extensions.connection):
        return conn.cursor(cursor_factory=DictCursor)
    return conn.cursor()


def init_db():
    with app.app_context():
        conn = get_connection()
        cursor = get_cursor()
        with app.open_resource('database.sql', mode='r') as f:
            if isinstance(conn, sqlite3.Connection):
                cursor.executescript(f.read())
            else:
                cursor.execute(f.read())
        conn.commit()
        conn.close()


# Импорт маршрутов перенесен в конец файла
from page_analyzer import routes  # noqa: E402, F401

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

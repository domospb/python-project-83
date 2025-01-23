from flask import Flask
import os
from dotenv import load_dotenv
import sqlite3
import psycopg2

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

DATABASE_URL = os.getenv('DATABASE_URL')

# SQL для инициализации базы данных
INIT_DATABASE_SQL = '''
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
    if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
        return psycopg2.connect(DATABASE_URL)
    else:
        sqlite_path = os.getenv('SQLITE_PATH', 'database.sqlite')
        return sqlite3.connect(sqlite_path)


def init_db():
    """Initialize the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        try:
            sql_script = INIT_DATABASE_SQL
            if isinstance(conn, sqlite3.Connection):
                # Для SQLite
                # Разделяем скрипт на отдельные команды и заменяем типы данных
                commands = sql_script.split(';')
                for command in commands:
                    if command.strip():
                        # Заменяем типы данных для SQLite
                        command = command.replace('SERIAL', 'INTEGER')
                        command = command.replace('TIMESTAMP', 'DATETIME')
                        cursor.execute(command)
            else:
                # Для PostgreSQL
                cursor.execute(sql_script)
            conn.commit()
        except Exception as e:
            print(f"Database initialization error: {str(e)}")
            raise
        finally:
            cursor.close()
    finally:
        conn.close()


# Инициализируем базу данных при запуске
with app.app_context():
    init_db()

# Импорт маршрутов перенесен в конец файла
from page_analyzer import routes  # noqa: E402, F401

if __name__ == '__main__':
    app.run(debug=True)

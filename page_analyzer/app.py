from flask import Flask
import os
from dotenv import load_dotenv
import sqlite3
import psycopg2

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


def init_db():
    """Initialize the database."""
    conn = get_connection()
    try:
        with app.open_resource('database.sql', mode='r') as f:
            sql_script = f.read()
            if isinstance(conn, sqlite3.Connection):
                # Для SQLite
                cur = conn.cursor()
                # Разделяем скрипт на отдельные команды
                commands = sql_script.split(';')
                for command in commands:
                    if command.strip():
                        # Заменяем SERIAL на INTEGER для SQLite
                        command = command.replace('SERIAL', 'INTEGER')
                        command = command.replace('TIMESTAMP', 'DATETIME')
                        cur.execute(command)
                cur.close()
            else:
                # Для PostgreSQL
                cur = conn.cursor()
                cur.execute(sql_script)
                cur.close()
            conn.commit()
    except Exception as e:
        print(f"Database initialization error: {str(e)}")
        raise
    finally:
        conn.close()


# Инициализируем базу данных при запуске
with app.app_context():
    init_db()

# Импорт маршрутов перенесен в конец файла
from page_analyzer import routes  # noqa: E402, F401

if __name__ == '__main__':
    app.run(debug=True)

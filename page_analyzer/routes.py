from flask import render_template, request, redirect, url_for, flash
from urllib.parse import urlparse
import validators
import psycopg2
import psycopg2.extras
import sqlite3
import requests
from page_analyzer.app import app, get_connection


def execute_query(cursor, query, params=None):
    """Execute a database query with proper error handling."""
    try:
        if isinstance(cursor, sqlite3.Cursor):
            # Для SQLite заменяем %s на ? и корректируем запросы
            query = query.replace('%s', '?')
            # Для RETURNING в SQLite
            if 'RETURNING' in query.upper():
                cursor.execute(query, params)
                return cursor.lastrowid
        else:
            # Для PostgreSQL заменяем ? на %s
            query = query.replace('?', '%s')
            cursor.execute(query, params)
            if 'RETURNING' in query.upper():
                return cursor.fetchone()[0]
    except Exception as e:
        print(f"Database error: {str(e)}")
        raise


@app.route('/')
def index():
    """Render the index page."""
    return render_template('index.html')


@app.route('/urls', methods=['POST'])
def add_url():
    """Add a new URL to the database."""
    url = request.form.get('url')

    if not url:
        flash('URL обязателен', 'danger')
        return render_template('index.html'), 422

    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    if not validators.url(normalized_url) or len(normalized_url) > 255:
        flash('Некорректный URL', 'danger')
        return render_template('index.html', url=url), 422

    conn = get_connection()
    cursor = conn.cursor()
    try:
        url_id = execute_query(
            cursor,
            'INSERT INTO urls (name) VALUES (?) RETURNING id',
            (normalized_url,)
        )
        conn.commit()
        flash('Страница успешно добавлена', 'success')
        return redirect(url_for('url_info', id=url_id))
    except (psycopg2.errors.UniqueViolation, sqlite3.IntegrityError):
        conn.rollback()
        execute_query(
            cursor,
            'SELECT id FROM urls WHERE name = ?',
            (normalized_url,)
        )
        url_id = cursor.fetchone()[0]
        flash('Страница уже существует', 'info')
        return redirect(url_for('url_info', id=url_id))
    finally:
        cursor.close()
        conn.close()


@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    """Create a new check for the specified URL."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, 'SELECT name FROM urls WHERE id = ?', (id,))
        url = cursor.fetchone()

        if not url:
            flash('Страница не найдена', 'danger')
            return redirect(url_for('urls_list'))

        try:
            response = requests.get(url[0])
            response.raise_for_status()
            execute_query(
                cursor,
                '''INSERT INTO url_checks (url_id, status_code)
                   VALUES (?, ?)''',
                (id, response.status_code)
            )
            conn.commit()
            flash('Страница успешно проверена', 'success')
        except requests.RequestException:
            flash('Произошла ошибка при проверке', 'danger')
        except Exception:
            conn.rollback()
            flash('Произошла ошибка при проверке', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('url_info', id=id))


@app.route('/urls/<int:id>')
def url_info(id):
    """Display information about a specific URL."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, 'SELECT * FROM urls WHERE id = ?', (id,))
        url = cursor.fetchone()

        if not url:
            flash('Страница не найдена', 'danger')
            return redirect(url_for('urls_list'))

        execute_query(
            cursor,
            '''SELECT * FROM url_checks
               WHERE url_id = ?
               ORDER BY created_at DESC''',
            (id,)
        )
        checks = cursor.fetchall()
        return render_template('url.html', url=url, checks=checks)
    finally:
        cursor.close()
        conn.close()


@app.route('/urls')
def urls_list():
    """Display a list of all URLs."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, '''
            SELECT
                urls.*,
                latest_checks.created_at as last_check_at,
                latest_checks.status_code as last_status_code
            FROM urls
            LEFT JOIN (
                SELECT DISTINCT ON (url_id)
                    url_id,
                    created_at,
                    status_code
                FROM url_checks
                ORDER BY url_id, created_at DESC
            ) latest_checks ON urls.id = latest_checks.url_id
            ORDER BY urls.created_at DESC
        ''')
        urls = cursor.fetchall()
        return render_template('urls.html', urls=urls)
    finally:
        cursor.close()
        conn.close()

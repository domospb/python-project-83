from flask import render_template, request, redirect, url_for, flash
from urllib.parse import urlparse
import validators
import psycopg2
import sqlite3
from page_analyzer.app import app, get_cursor, get_connection


def execute_query(cursor, query, params=None):
    """Execute a database query with proper error handling."""
    if isinstance(cursor, psycopg2.extensions.cursor):
        query = query.replace('?', '%s')

    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
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
    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    if not validators.url(normalized_url) or len(normalized_url) > 255:
        flash('Некорректный URL', 'danger')
        return render_template('index.html', url=url), 422

    conn = get_connection()
    cursor = get_cursor()

    try:
        execute_query(
            cursor,
            'INSERT INTO urls (name) VALUES (?) RETURNING id',
            (normalized_url,)
        )
        url_id = cursor.fetchone()[0]
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
        existing_url = cursor.fetchone()
        flash('Страница уже существует', 'info')
        return redirect(url_for('url_info', id=existing_url[0]))
    except Exception as e:
        conn.rollback()
        flash(f'Произошла ошибка: {str(e)}', 'danger')
        return render_template('index.html', url=url), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/urls/<int:id>')
def url_info(id):
    """Display information about a specific URL."""
    conn = get_connection()
    cursor = get_cursor()
    execute_query(cursor, 'SELECT * FROM urls WHERE id = ?', (id,))
    url = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('url.html', url=url)


@app.route('/urls')
def urls_list():
    """Display a list of all URLs."""
    conn = get_connection()
    cursor = get_cursor()
    execute_query(cursor, 'SELECT * FROM urls ORDER BY created_at DESC')
    urls = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('urls.html', urls=urls)

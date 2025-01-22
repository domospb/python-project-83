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
        if isinstance(cursor, psycopg2.extensions.cursor):
            query = query.replace('?', '%s')
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

    with get_connection() as conn:
        with conn.cursor() as cursor:
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


@app.route('/urls/<int:id>')
def url_info(id):
    """Display information about a specific URL."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            execute_query(cursor, 'SELECT * FROM urls WHERE id = ?', (id,))
            url = cursor.fetchone()

            execute_query(
                cursor,
                '''SELECT * FROM url_checks
                   WHERE url_id = ?
                   ORDER BY created_at DESC''',
                (id,)
            )
            checks = cursor.fetchall()

    return render_template('url.html', url=url, checks=checks)


@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    """Create a new check for the specified URL."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Получаем URL для проверки
            execute_query(
                cursor,
                'SELECT name FROM urls WHERE id = ?',
                (id,)
            )
            url = cursor.fetchone()
            if not url:
                flash('Страница не найдена', 'danger')
                return redirect(url_for('urls_list'))

            try:
                response = requests.get(url[0])
                response.raise_for_status()  # Проверка статуса ответа
                status_code = response.status_code

                # Создаем запись о проверке
                execute_query(
                    cursor,
                    '''INSERT INTO url_checks (url_id, status_code)
                       VALUES (?, ?)''',
                    (id, status_code)
                )
                conn.commit()
                flash('Страница успешно проверена', 'success')

            except requests.RequestException:
                conn.rollback()
                flash('Произошла ошибка при проверке', 'danger')
            except Exception:  # Убрали неиспользуемую переменную e
                conn.rollback()
                flash('Произошла ошибка при проверке', 'danger')

    return redirect(url_for('url_info', id=id))


@app.route('/urls')
def urls_list():
    """Display a list of all URLs."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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

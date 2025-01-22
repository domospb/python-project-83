from flask import render_template, request, redirect, url_for, flash
from urllib.parse import urlparse
import validators
import psycopg2
import psycopg2.extras
import sqlite3
import requests
from bs4 import BeautifulSoup
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


def get_seo_data(html_content):
    """Extract SEO data from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    h1_tag = soup.find('h1')
    title_tag = soup.find('title')
    description_tag = soup.find('meta', attrs={'name': 'description'})

    return {
        'h1': h1_tag.text.strip() if h1_tag else None,
        'title': title_tag.text.strip() if title_tag else None,
        'description': (
            description_tag.get('content', '').strip()
            if description_tag else None
        )
    }


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
                response.raise_for_status()
                status_code = response.status_code

                # Извлекаем SEO-данные
                seo_data = get_seo_data(response.text)

                # Создаем запись о проверке
                execute_query(
                    cursor,
                    '''INSERT INTO url_checks
                       (url_id, status_code, h1, title, description)
                       VALUES (?, ?, ?, ?, ?)''',
                    (id, status_code, seo_data['h1'],
                     seo_data['title'], seo_data['description'])
                )
                conn.commit()
                flash('Страница успешно проверена', 'success')

            except requests.RequestException:
                conn.rollback()
                flash('Произошла ошибка при проверке', 'danger')
            except Exception:
                conn.rollback()
                flash('Произошла ошибка при проверке', 'danger')

    return redirect(url_for('url_info', id=id))


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

from flask import (render_template, request, redirect,
                  url_for, flash, make_response)
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
    
    if not url:
        flash('URL обязателен', 'danger')
        return render_template('index.html'), 422

    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    if not validators.url(normalized_url) or len(normalized_url) > 255:
        flash('Некорректный URL', 'danger')
        response = make_response(render_template('index.html', url=url))
        response.status_code = 422
        return response

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO urls (name) VALUES (%s) RETURNING id',
            (normalized_url,)
        )
        url_id = cursor.fetchone()[0]
        conn.commit()
        flash('Страница успешно добавлена', 'success')
        return redirect(url_for('url_info', id=url_id))
    except (psycopg2.errors.UniqueViolation, sqlite3.IntegrityError):
        conn.rollback()
        cursor.execute(
            'SELECT id FROM urls WHERE name = %s',
            (normalized_url,)
        )
        existing_url = cursor.fetchone()
        flash('Страница уже существует', 'info')
        return redirect(url_for('url_info', id=existing_url[0]))
    finally:
        cursor.close()
        conn.close()


@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    """Create a new check for the specified URL."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT name FROM urls WHERE id = %s', (id,))
        url = cursor.fetchone()
        
        if not url:
            flash('Страница не найдена', 'danger')
            return redirect(url_for('urls_list'))

        try:
            response = requests.get(url[0])
            response.raise_for_status()
            
            seo_data = get_seo_data(response.text)
            
            cursor.execute(
                '''INSERT INTO url_checks
                   (url_id, status_code, h1, title, description)
                   VALUES (%s, %s, %s, %s, %s)''',
                (id, response.status_code, seo_data['h1'],
                 seo_data['title'], seo_data['description'])
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
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute('SELECT * FROM urls WHERE id = %s', (id,))
        url = cursor.fetchone()

        if not url:
            flash('Страница не найдена', 'danger')
            return redirect(url_for('urls_list'))

        cursor.execute(
            '''SELECT * FROM url_checks
               WHERE url_id = %s
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
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cursor.execute('''
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

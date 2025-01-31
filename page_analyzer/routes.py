from flask import render_template, request, redirect, url_for, flash
from urllib.parse import urlparse
import validators
import requests
from bs4 import BeautifulSoup
from page_analyzer.app import app
from page_analyzer.db_manager import get_db_cursor
import logging


# Set up logging
logger = logging.getLogger(__name__)


def normalize_url(url):
    """Normalize URL by removing path, query parameters, and fragments."""
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def get_seo_data(html_content):
    """Extract SEO data from HTML content."""
    try:
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
    except Exception as e:
        logger.error(f"Error parsing HTML content: {str(e)}")
        raise


@app.route('/')
def index():
    """Render the index page."""
    logger.info("Accessing index page")
    return render_template('index.html')


@app.route('/urls', methods=['POST'])
def add_url():
    """Add a new URL to the database."""
    url = request.form.get('url')
    logger.info(f"Attempting to add URL: {url}")

    if not url:
        logger.warning("Empty URL submitted")
        flash('URL обязателен', 'danger')
        return render_template('index.html'), 422

    normalized_url = normalize_url(url)

    if not validators.url(normalized_url) or len(normalized_url) > 255:
        logger.warning(f"Invalid URL submitted: {normalized_url}")
        flash('Некорректный URL', 'danger')
        return render_template('index.html', url=url), 422

    try:
        with get_db_cursor() as cursor:
            # Check if URL exists
            cursor.execute(
                'SELECT id FROM urls WHERE name = %s',
                (normalized_url,)
            )
            existing_url = cursor.fetchone()

            if existing_url:
                logger.info(f"URL already exists: {normalized_url}")
                flash('Страница уже существует', 'info')
                return redirect(url_for('url_info', id=existing_url['id']))

            # Add new URL
            cursor.execute(
                'INSERT INTO urls (name) VALUES (%s) RETURNING id',
                (normalized_url,)
            )
            url_id = cursor.fetchone()['id']
            logger.info(f"Successfully added URL: {normalized_url}")
            flash('Страница успешно добавлена', 'success')
            return redirect(url_for('url_info', id=url_id))

    except Exception as e:
        logger.error(f"Error adding URL: {str(e)}")
        flash('Произошла ошибка при добавлении страницы', 'danger')
        return render_template('index.html', url=url), 500


@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    """Create a new check for the specified URL."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                'SELECT name FROM urls WHERE id = %s',
                (id,)
            )
            url = cursor.fetchone()
            if not url:
                logger.warning(f"URL not found for id: {id}")
                flash('Страница не найдена', 'danger')
                return redirect(url_for('urls_list'))

            try:
                response = requests.get(url['name'])
                response.raise_for_status()
                status_code = response.status_code
                seo_data = get_seo_data(response.text)

                cursor.execute(
                    '''INSERT INTO url_checks
                       (url_id, status_code, h1, title, description)
                       VALUES (%s, %s, %s, %s, %s)''',
                    (id, status_code, seo_data['h1'],
                     seo_data['title'], seo_data['description'])
                )
                logger.info(f"URL check completed for id {id}")
                flash('Страница успешно проверена', 'success')
            except requests.RequestException as e:
                logger.error(f"Request error checking URL: {str(e)}")
                flash('Произошла ошибка при проверке', 'danger')
    except Exception as e:
        logger.error(f"Database error checking URL: {str(e)}")
        flash('Произошла ошибка при проверке', 'danger')

    return redirect(url_for('url_info', id=id))


@app.route('/urls/<int:id>')
def url_info(id):
    """Display information about a specific URL."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('SELECT * FROM urls WHERE id = %s', (id,))
            url = cursor.fetchone()
            if not url:
                logger.warning(f"URL not found for id: {id}")
                flash('Страница не найдена', 'danger')
                return redirect(url_for('urls_list'))

            cursor.execute(
                '''SELECT * FROM url_checks
                   WHERE url_id = %s
                   ORDER BY created_at DESC''',
                (id,)
            )
            checks = cursor.fetchall()
            logger.info(f"Retrieved URL info for id {id}")
            return render_template('url.html', url=url, checks=checks)

    except Exception as e:
        logger.error(f"Error retrieving URL info: {str(e)}")
        flash('Произошла ошибка', 'danger')
        return redirect(url_for('urls_list'))


@app.route('/urls')
def urls_list():
    """Display a list of all URLs."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                '''SELECT
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
                   ORDER BY urls.created_at DESC'''
            )
            urls = cursor.fetchall()
            logger.info("Retrieved URLs list")
            return render_template('urls.html', urls=urls)

    except Exception as e:
        logger.error(f"Error retrieving URLs list: {str(e)}")
        flash('Произошла ошибка при получении списка URL', 'danger')
        return redirect(url_for('index'))

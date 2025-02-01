import logging

import requests
from flask import flash, redirect, render_template, request, url_for

from .app import app
from .db_manager import URLRepository, get_db_cursor
from .html_manager import get_seo_data
from .validation_manager import normalize_url, validate_url

logger = logging.getLogger(__name__)


@app.route('/')
def index():
    logger.info('Accessing index page')
    return render_template('index.html')


@app.route('/urls', methods=['POST'])
def add_url():
    url = request.form.get('url')
    logger.info(f'Attempting to add URL: {url}')

    is_valid, error_message = validate_url(url)
    if not is_valid:
        flash(error_message, 'danger')
        return render_template('index.html', url=url), 422

    normalized_url = normalize_url(url)

    try:
        with get_db_cursor() as cursor:
            existing_url = URLRepository.find_by_name(cursor, normalized_url)

            if existing_url:
                logger.info(f'URL already exists: {normalized_url}')
                flash('Страница уже существует', 'info')
                return redirect(url_for('url_info', id=existing_url['id']))

            url_id = URLRepository.create(cursor, normalized_url)
            logger.info(f'Successfully added URL: {normalized_url}')
            flash('Страница успешно добавлена', 'success')
            return redirect(url_for('url_info', id=url_id))

    except Exception as e:
        logger.error(f'Error adding URL: {str(e)}')
        flash('Произошла ошибка при добавлении страницы', 'danger')
        return render_template('index.html', url=url), 500


@app.route('/urls/<int:id>/checks', methods=['POST'])
def check_url(id):
    try:
        with get_db_cursor() as cursor:
            cursor.execute('SELECT name FROM urls WHERE id = %s', (id,))
            url = cursor.fetchone()
            if not url:
                logger.warning(f'URL not found for id: {id}')
                flash('Страница не найдена', 'danger')
                return redirect(url_for('urls_list'))

            try:
                response = requests.get(url['name'])
                response.raise_for_status()
                status_code = response.status_code
                seo_data = get_seo_data(response.text)

                cursor.execute(
                    """INSERT INTO url_checks
                       (url_id, status_code, h1, title, description)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        id,
                        status_code,
                        seo_data['h1'],
                        seo_data['title'],
                        seo_data['description'],
                    ),
                )
                logger.info(f'URL check completed for id {id}')
                flash('Страница успешно проверена', 'success')
            except requests.RequestException as e:
                logger.error(f'Request error checking URL: {str(e)}')
                flash('Произошла ошибка при проверке', 'danger')
    except Exception as e:
        logger.error(f'Database error checking URL: {str(e)}')
        flash('Произошла ошибка при проверке', 'danger')

    return redirect(url_for('url_info', id=id))


@app.route('/urls/<int:id>')
def url_info(id):
    try:
        with get_db_cursor() as cursor:
            cursor.execute('SELECT * FROM urls WHERE id = %s', (id,))
            url = cursor.fetchone()
            if not url:
                logger.warning(f'URL not found for id: {id}')
                flash('Страница не найдена', 'danger')
                return redirect(url_for('urls_list'))

            cursor.execute(
                """SELECT * FROM url_checks
                   WHERE url_id = %s
                   ORDER BY created_at DESC""",
                (id,),
            )
            checks = cursor.fetchall()
            logger.info(f'Retrieved URL info for id {id}')
            return render_template('url.html', url=url, checks=checks)

    except Exception as e:
        logger.error(f'Error retrieving URL info: {str(e)}')
        flash('Произошла ошибка', 'danger')
        return redirect(url_for('urls_list'))


@app.route('/urls')
def urls_list():
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """SELECT
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
                   ORDER BY urls.created_at DESC"""
            )
            urls = cursor.fetchall()
            logger.info('Retrieved URLs list')
            return render_template('urls.html', urls=urls)

    except Exception as e:
        logger.error(f'Error retrieving URLs list: {str(e)}')
        flash('Произошла ошибка при получении списка URL', 'danger')
        return redirect(url_for('index'))

import logging
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import DictCursor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('page_analyzer.log'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    'DATABASE_URL', 'postgresql://postgres:password@db:5432/postgres'
)


@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
        conn.commit()
        logger.info('Database transaction committed successfully')
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(f'Database transaction rolled back. Error: {str(e)}')
        raise
    finally:
        if conn:
            conn.close()
            logger.info('Database connection closed')


@contextmanager
def get_db_cursor():
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            yield cursor
        finally:
            cursor.close()


class URLRepository:
    @staticmethod
    def find_by_name(cursor, url_name):
        query = 'SELECT id FROM urls WHERE name = %s'
        cursor.execute(query, (url_name,))
        return cursor.fetchone()

    @staticmethod
    def create(cursor, url_name):
        query = 'INSERT INTO urls (name) VALUES (%s) RETURNING id'
        cursor.execute(query, (url_name,))
        return cursor.fetchone()['id']

    @staticmethod
    def find_by_id(cursor, url_id):
        cursor.execute('SELECT * FROM urls WHERE id = %s', (url_id,))
        return cursor.fetchone()

    @staticmethod
    def get_all_with_checks(cursor):
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
        return cursor.fetchall()


class CheckRepository:
    @staticmethod
    def create(cursor, url_id, status_code, seo_data):
        cursor.execute(
            """INSERT INTO url_checks
               (url_id, status_code, h1, title, description)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                url_id,
                status_code,
                seo_data['h1'],
                seo_data['title'],
                seo_data['description'],
            ),
        )

    @staticmethod
    def get_all_for_url(cursor, url_id):
        cursor.execute(
            """SELECT * FROM url_checks
               WHERE url_id = %s
               ORDER BY created_at DESC""",
            (url_id,),
        )
        return cursor.fetchall()

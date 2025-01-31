from contextlib import contextmanager
import psycopg2
from psycopg2.extras import DictCursor
from flask import current_app
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('page_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = psycopg2.connect(current_app.config['DATABASE_URL'])
        conn.autocommit = False
        yield conn
        conn.commit()
        logger.info("Database transaction committed successfully")
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(f"Database transaction rolled back due to error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")

@contextmanager
def get_db_cursor(commit=False):
    """Context manager for database cursors."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        finally:
            cursor.close()

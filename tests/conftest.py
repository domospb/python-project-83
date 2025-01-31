import pytest
import psycopg2
import os
from page_analyzer.app import app
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture(scope='session')
def test_app():
    app.config['TESTING'] = True
    return app

@pytest.fixture(scope='session')
def test_client(test_app):
    return test_app.test_client()

@pytest.fixture(scope='function')
def db():
    """Create test database and tables."""
    database_url = os.getenv('DATABASE_URL')
    
    # Setup - create tables
    with psycopg2.connect(database_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            with open('database.sql', 'r') as f:
                cursor.execute(f.read())
    
    yield database_url
    
    # Teardown - clean up tables
    with psycopg2.connect(database_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute('''
                TRUNCATE url_checks, urls RESTART IDENTITY CASCADE;
            ''')

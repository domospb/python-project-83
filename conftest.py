import pytest
import psycopg2
import os
from page_analyzer.app import app

@pytest.fixture(scope='session')
def test_db():
    """Create test database and tables"""
    test_db_url = os.getenv('TEST_DATABASE_URL')
    
    # Create test database
    with psycopg2.connect(test_db_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            # Read and execute database schema
            with open('database.sql', 'r') as f:
                cursor.execute(f.read())
    
    yield test_db_url
    
    # Cleanup after tests
    with psycopg2.connect(test_db_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute('''
                DROP TABLE IF EXISTS url_checks;
                DROP TABLE IF EXISTS urls;
            ''')

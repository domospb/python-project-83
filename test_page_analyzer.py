import pytest
from page_analyzer.app import app
from page_analyzer.db_manager import get_db_connection, get_db_cursor
import psycopg2
import os

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['DATABASE_URL'] = os.getenv('TEST_DATABASE_URL')
    
    with app.test_client() as client:
        yield client

def test_index_page(client):
    """Test index page loads correctly"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'SEO' in response.data

def test_add_valid_url(client):
    """Test adding a valid URL"""
    url = 'https://example.com'
    response = client.post('/urls', data={'url': url})
    assert response.status_code == 302  # Redirect after successful addition

def test_add_invalid_url(client):
    """Test adding an invalid URL"""
    url = 'not-a-url'
    response = client.post('/urls', data={'url': url})
    assert response.status_code == 422

def test_db_connection():
    """Test database connection context manager"""
    try:
        with get_db_connection() as conn:
            assert conn is not None
            assert not conn.closed
    except Exception as e:
        pytest.fail(f"Database connection failed: {str(e)}")

def test_url_checks(client):
    """Test URL checking functionality"""
    # First add a URL
    url = 'https://example.com'
    response = client.post('/urls', data={'url': url})
    assert response.status_code == 302
    
    # Then check the URL info page
    with get_db_cursor() as cursor:
        cursor.execute('SELECT id FROM urls WHERE name = %s', (url,))
        url_id = cursor.fetchone()['id']
        
    response = client.get(f'/urls/{url_id}')
    assert response.status_code == 200

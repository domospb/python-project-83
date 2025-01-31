import pytest
from page_analyzer.db_manager import get_db_cursor


def test_index_page(test_client):
    """Test index page loads correctly."""
    response = test_client.get('/')
    assert response.status_code == 200
    assert 'Анализатор страниц' in response.get_data(as_text=True)


def test_add_valid_url(test_client, db):
    """Test adding a valid URL."""
    url = 'https://example.com'
    response = test_client.post('/urls', data={'url': url}, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify URL was added to database
    with get_db_cursor() as cursor:
        cursor.execute('SELECT name FROM urls WHERE name = %s', (url,))
        result = cursor.fetchone()
        assert result is not None
        assert result['name'] == url


def test_add_invalid_url(test_client):
    """Test adding an invalid URL."""
    response = test_client.post('/urls', data={'url': 'not-a-url'})
    assert response.status_code == 422


def test_duplicate_url(test_client, db):
    """Test adding the same URL twice."""
    url = 'https://example.com'
    
    # Add URL first time
    response1 = test_client.post('/urls', data={'url': url}, follow_redirects=True)
    assert response1.status_code == 200
    
    # Try to add same URL again
    response2 = test_client.post('/urls', data={'url': url}, follow_redirects=True)
    assert response2.status_code == 200
    assert 'Страница уже существует' in response2.get_data(as_text=True)


def test_url_check(test_client, db):
    """Test URL checking functionality."""
    # First add a URL
    url = 'https://example.com'
    response = test_client.post('/urls', data={'url': url}, follow_redirects=True)
    assert response.status_code == 200
    
    # Get the URL ID
    with get_db_cursor() as cursor:
        cursor.execute('SELECT id FROM urls WHERE name = %s', (url,))
        url_id = cursor.fetchone()['id']
    
    # Check URL info page
    response = test_client.get(f'/urls/{url_id}')
    assert response.status_code == 200

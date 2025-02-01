import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def get_seo_data(html_content):
    """Extract SEO data from HTML content."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        h1_tag = soup.find('h1')
        title_tag = soup.find('title')
        description_tag = soup.find('meta', attrs={'name': 'description'})

        has_desc = description_tag is not None
        desc_text = description_tag.get('content', '') if has_desc else None
        desc_value = desc_text.strip() if desc_text else None

        return {
            'h1': h1_tag.text.strip() if h1_tag else None,
            'title': title_tag.text.strip() if title_tag else None,
            'description': desc_value,
        }
    except Exception as e:
        logger.error(f'Error parsing HTML content: {str(e)}')
        raise

from urllib.parse import urlparse

import validators


def normalize_url(url):
    """Normalize the given URL."""
    parsed_url = urlparse(url)
    return f'{parsed_url.scheme}://{parsed_url.netloc}'


def validate_url(url):
    """
    Validate URL and return tuple (is_valid, error_message).
    """
    if not url:
        return False, 'URL обязателен'

    normalized_url = normalize_url(url)
    if not validators.url(normalized_url) or len(normalized_url) > 255:
        return False, 'Некорректный URL'

    return True, None

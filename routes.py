@app.route('/urls', methods=['POST']) 
def add_url():
    """Add a new URL to the database."""
    url = request.form.get('url')

    if not url:
        flash('URL обязателен', 'danger') 
        return render_template('index.html'), 422

    parsed_url = urlparse(url)
    path = parsed_url.path.rstrip('/')
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{path}"

    if not validators.url(normalized_url) or len(normalized_url) > 255:
        flash('Некорректный URL', 'danger')
        return render_template('index.html', url=url), 422

    conn = get_connection()
    try:
        cursor = conn.cursor()
        try:
            # Check if URL exists 
            execute_query(
                cursor,
                'SELECT id FROM urls WHERE name = ?',
                (normalized_url,)
            )
            existing_url = cursor.fetchone()

            if existing_url:
                flash('Страница уже существует', 'info')
                return redirect(url_for('url_info', id=existing_url[0]))

            # Get SEO data
            html_content = requests.get(normalized_url).text
            seo_data = get_seo_data(html_content)
            # Add new URL with SEO data if it doesn't exist
            execute_query(
                cursor,
                '''INSERT INTO urls (name, h1, title, description) 
                   VALUES (?, ?, ?, ?) RETURNING id''',
                (normalized_url, seo_data['h1'], 
                 seo_data['title'], seo_data['description'])
            )
            url_id = cursor.fetchone()[0]
            conn.commit()
            flash('Страница успешно добавлена', 'success')
            return redirect(url_for('url_info', id=url_id))

        except Exception:
            conn.rollback()
            flash('Произошла ошибка при добавлении страницы', 'danger')
            return render_template('index.html', url=url), 500
        finally:
            cursor.close()
    finally:
        conn.close()

def get_seo_data(html_content):
    """Extract SEO data from HTML content."""
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
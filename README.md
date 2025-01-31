### Hexlet tests and linter status:
[![Actions Status](https://github.com/domospb/python-project-83/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/domospb/python-project-83/actions)

https://python-project-83-xy83.onrender.com/

## Page Analyzer

A web application that analyzes specified pages for SEO suitability. The service performs primary analysis of the website's SEO compatibility by checking HTML elements important for search engines.

## Features

- URL validation and normalization
- SEO analysis including:
  - Page title extraction
  - Meta description analysis
  - H1 headers detection
- HTTP response code tracking
- Historical checks data storage
- Clean and user-friendly interface
- Comprehensive logging system

## Technology Stack

| Tool              | Version |
|-------------------|---------|
| Python            | 3.10+   |
| Flask             | 3.0.3   |
| PostgreSQL        | Latest  |
| UV                | Latest  |
| Gunicorn          | 22.0.0  |
| Python-dotenv     | 1.0.1   |
| Psycopg2-binary   | 2.9.9   |
| Validators        | 0.33.0  |
| Requests          | 2.31.0  |
| BeautifulSoup4    | 4.12.0  |
| Ruff              | 0.9.4   |

## Installation

### Prerequisites
- Python (3.10 or higher)
- UV package manager
- PostgreSQL
- Make (for using Makefile commands)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/domospb/python-project-83.git
cd python-project-83
```

2. Install dependencies using UV:
```bash
make install
```

3. Create `.env` file with required variables:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/database_name
SECRET_KEY=your-secret-key
```

4. Initialize database:
```bash
make setup
```

## Development

Start the development server:
```bash
make dev
```

## Production

Run with Gunicorn:
```bash
make start
```

## Database Structure

The application uses two main tables (defined in `database.sql`):
- `urls`: Stores website URLs and creation timestamps
  - id (SERIAL PRIMARY KEY)
  - name (VARCHAR(255) NOT NULL)
  - created_at (TIMESTAMP)

- `url_checks`: Stores SEO analysis results
  - id (SERIAL PRIMARY KEY)
  - url_id (INTEGER REFERENCES urls)
  - status_code (INTEGER)
  - h1 (VARCHAR(255))
  - title (VARCHAR(255))
  - description (TEXT)
  - created_at (TIMESTAMP)

## Code Quality

The project maintains high code quality standards through:
- Ruff linter for code style checking
- Comprehensive logging system
- Clean code practices
- Proper error handling

Run code quality checks:
```bash
make lint
```

## CI/CD

The project uses GitHub Actions for continuous integration with two workflows:
- `hexlet-check.yml`: Automated project verification
- `p-83.yml`: Custom CI pipeline including:
  - Python 3.10 setup
  - UV installation and dependency management
  - Code style checks with Ruff
  - Project structure verification

## Project Structure

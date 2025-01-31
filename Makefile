install:
	uv sync

setup:
	pip3 install uv
	make install
	psql -d ${DATABASE_URL} -f database.sql

lint:
	uv run flake8 page_analyzer/

dev:
	uv run flask --app page_analyzer:app run

PORT ?= 8000
start:
	uv run gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app

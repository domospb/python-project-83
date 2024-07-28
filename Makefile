install:
	poetry install

lint:
	poetry run flake8 page_analyzer/

dev:
	poetry run flask --app page_analyzer:app run


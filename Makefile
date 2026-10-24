PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: setup install fetch quickstart test lint typecheck check run animate docker-build clean

setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip

install: setup
	$(PIP) install -r requirements-dev.txt

fetch:
	$(PY) scripts/fetch_data.py

quickstart:
	$(PY) main.py

run:
	.venv/bin/streamlit run app.py

animate:
	$(PY) scripts/export_animation.py --format mp4

docker-build:
	docker build -t space-weather-observatory .

test:
	$(PY) -m pytest

lint:
	.venv/bin/ruff check .

typecheck:
	.venv/bin/mypy src

check: lint typecheck test

clean:
	rm -rf output/*.png output/*.gif output/*.mp4 output/*.json

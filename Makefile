.PHONY: install run demo ingest test fmt

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --port 8000

demo:
	python -m scripts.demo

ingest:
	python -m scripts.ingest

test:
	pytest

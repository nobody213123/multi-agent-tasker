.PHONY: install run test lint typecheck clean docker-build docker-run

install:
	pip install -r requirements.txt
	playwright install chromium

run:
	python main.py

test:
	pytest tests/ -v --tb=short

lint:
	ruff check .

typecheck:
	mypy .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t multi-agent-tasker .

docker-run:
	docker run -p 8080:8080 \
		--env-file .env \
		multi-agent-tasker

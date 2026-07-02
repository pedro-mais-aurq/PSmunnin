
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY src/ ./src/
ENV PYTHONPATH=/app/src

CMD ["celery", "-A", "leadhunter_worker.celery_app.app", "worker", "--loglevel=info"]

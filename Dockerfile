FROM python:3.12-slim
WORKDIR /project

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir "poetry==2.4.1"
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-directory

COPY app/ ./app/
COPY alembic ./alembic/
COPY alembic.ini ./
COPY run.py ./

RUN useradd -m appuser \
    && mkdir -p /data/storage \
    && chown -R appuser:appuser /data/storage /project
USER appuser

EXPOSE 8000

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]

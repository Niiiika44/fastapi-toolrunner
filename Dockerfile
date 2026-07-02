# ---------- build stage ----------
FROM python:3.12-slim AS builder

WORKDIR /project

ENV PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true

RUN pip install --no-cache-dir "poetry==2.4.1"
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-directory

# ---------- runtime stage ----------
FROM python:3.12-slim AS runtime

WORKDIR /project

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/project/.venv/bin:$PATH"

COPY --from=builder /project/.venv /project/.venv

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

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org pypi.python.org" \
    POETRY_VERSION=2.1.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libpq-dev \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Prefer Poetry when lock is valid; fall back to requirements.txt for installs.
COPY requirements.txt pyproject.toml poetry.lock* ./
RUN pip install --upgrade pip \
    && pip install "poetry==${POETRY_VERSION}" \
    && if [ -f poetry.lock ]; then \
         poetry install --no-root --only main || pip install -r requirements.txt; \
       else \
         pip install -r requirements.txt; \
       fi

COPY manage.py ./
COPY core ./core
COPY users ./users
COPY accounts ./accounts
COPY projects ./projects
COPY templates ./templates
COPY docker/entrypoint.sh /app/docker/entrypoint.sh

RUN mkdir -p /app/data /app/media /app/staticfiles \
    && chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]

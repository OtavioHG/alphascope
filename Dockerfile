FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements.txt
COPY requirements-full.txt requirements-full.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements-full.txt

COPY pyproject.toml pyproject.toml
COPY README.md README.md
COPY src src
COPY config config
COPY deployment deployment
COPY frontend frontend
COPY docs docs
COPY alembic.ini alembic.ini
COPY alembic alembic

RUN pip install --no-cache-dir -e .

EXPOSE 8000 8010 8501 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "from pathlib import Path; import sys; sys.exit(0 if Path('src/alphascope/cli.py').exists() else 1)"

CMD ["python", "-m", "alphascope.cli", "run-platform-api", "--host", "0.0.0.0", "--port", "8010"]

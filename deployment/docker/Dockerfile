FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip && pip install -e .

EXPOSE 8000 8501

CMD ["python", "-m", "alphascope.cli", "run-api"]

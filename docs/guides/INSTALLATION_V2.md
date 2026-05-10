# Instalação V2

## Local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Controle profissional

```bash
alphascope-cc dashboard
python -m alphascope.cli control-center
python -m alphascope.cli run-platform-api --host 0.0.0.0 --port 8010
```

## Docker

```bash
docker compose up --build
```

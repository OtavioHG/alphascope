# Uso V2

## CLI/TUI

```bash
alphascope-cc dashboard
alphascope-cc tui
python -m alphascope.cli platform-status
```

## API

```bash
python -m alphascope.cli run-platform-api --host 0.0.0.0 --port 8010
```

Endpoints principais:

- `GET /healthz`
- `GET /dashboard`
- `GET /ranking`
- `GET /positions`
- `GET /history`
- `GET /risk`
- `GET /config`
- `GET /audit`
- `POST /entry/evaluate`
- `POST /exit/evaluate`
- `POST /risk/evaluate`
- `POST /orders/validate`

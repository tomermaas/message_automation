# Message Automation

This repository now includes a small FastAPI backend and a React + Vite frontend
for a card based messages UI.

## Backend

```bash
python3 -m app.main
```

The API listens on `http://127.0.0.1:8765`.

## Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

The frontend uses `VITE_API_BASE` to locate the backend (defaults to
`http://127.0.0.1:8765`).

## Testing

Run the backend unit tests with:

```bash
pytest
```


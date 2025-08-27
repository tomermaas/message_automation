# Message Automation

Message Automation provides a FastAPI backend and a React + Vite frontend for managing course messages. The application is designed for local desktop use—no cloud deployment is required. When packaged, users install the executable and run everything on their own machine. Each user's data stays local; databases are created under the `data/` directory next to the executable by default. Set the `DATA_ROOT` environment variable to change this location.

Edit the provided `.env` and supply `KIDUM_USERNAME` and `KIDUM_PASSWORD` before running or packaging the app. Override `LMS_BASE_URL` and `LMS_API_BASE_URL` if you need to target a non-production environment. The packaged executable bundles this `.env` so end users do not configure anything.

## Backend

Install dependencies and run the server:

```bash
pip install -r requirements.txt
python3 -m app.main
```

The API listens on `http://127.0.0.1:8765`.

## Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

The frontend uses the `VITE_API_BASE` environment variable to locate the backend (defaults to `http://127.0.0.1:8765`).

## Packaging

Build the frontend and generate a self-contained installer:

```bash
pnpm --dir frontend build
pip install pyinstaller
sudo apt-get install -y makeself # or: brew install makeself
scripts/make_installer.sh
```

The script runs PyInstaller using `build/message_automation.spec` and then wraps the output in a self-extracting archive at `installer/message_automation.run`. Distribute that file to end users—they execute it, the bundled app extracts, and their browser opens on `127.0.0.1:8765`. Databases live under `data/` next to the executable. Make sure `.env` contains the required credentials before packaging so users have nothing to configure.

## Testing

Run the backend unit tests with:

```bash
pytest
```

The optional live browser test requires Playwright and real credentials. Provide `KIDUM_USERNAME` and `KIDUM_PASSWORD` and enable it with `RUN_LIVE_BROWSER_TEST=1` if you want to run it.

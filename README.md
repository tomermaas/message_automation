# Message Automation

Message Automation is a desktop-focused utility for synchronising and editing course messages from the Kidum learning management system (LMS).  The project bundles a FastAPI backend, a React + Vite frontend and browser automation helpers.  Everything runs on the user's machine; databases and credentials never leave the local environment.

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Project Layout](#project-layout)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Local Development](#local-development)
  - [Backend](#backend)
  - [Frontend](#frontend)
  - [Tests](#tests)
- [Data Storage](#data-storage)
- [Packaging and Distribution](#packaging-and-distribution)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- **Local-only operation** – the application logs in to the Kidum LMS and synchronises course data without sending anything to external servers.
- **SQLite databases** – each course has its own message and distance databases under `data/courses/<teacher_id>/<course_id>/`.
- **Web interface** – a React + Vite frontend served from the backend at `http://127.0.0.1:8765` for editing, patching and sanitising message content.
- **Desktop login** – a PySide6 window manages the login flow and class selection while automation runs in a background thread.
- **Optional distance analysis** – `/debug` routes expose helpers such as gap calculations for each student.
- **Self-contained packaging** – PyInstaller and `makeself` produce a single installer for end users.

## Architecture

### Backend
The FastAPI backend (`app/`) serves HTML routes, REST endpoints and static files.  On startup it also launches the default web browser pointing at the local interface.  Configuration values are read from environment variables via `dotenv`.

### Frontend
The frontend (`frontend/`) is built with React, Vite and Tailwind CSS.  It communicates with the backend through REST calls; the base URL is controlled by the `VITE_API_BASE` environment variable.

### Automation
Automation helpers live in `automation/` and communicate with the LMS via its HTTP API. The `AutomationWorker` class performs login, course enumeration and selection in a background thread so the PySide6 UI remains responsive.

### Data Layer
Per-course SQLite databases store messages and distance information.  `app/services/paths.py` computes paths based on the `DATA_ROOT` configuration and optional environment names derived from `LMS_BASE_URL`.

## Project Layout

```
app/           FastAPI application and service layer
automation/    LMS API helpers and background automation
frontend/      React + Vite user interface
ui/            PySide6 desktop windows (login and class selection)
build/         PyInstaller specification
scripts/       Helper scripts for packaging and maintenance
tests/         Python unit and integration tests
design/        Design assets and mockups
logic/         Experimentation and prototypes
```

## Prerequisites

- Python 3.11+ with pip
- Node.js 18+ and [pnpm](https://pnpm.io) for the frontend
- `makeself` for bundling the installer (`apt-get install -y makeself` or `brew install makeself`)

## Configuration

Create a `.env` file next to the executable or at the repository root during development.  Populate the following variables:

```
KIDUM_USERNAME=<your username>
KIDUM_PASSWORD=<your password>
LMS_BASE_URL=https://kidum-me.com
LMS_API_BASE_URL=https://lmsapi.kidum-me.com
DATA_ROOT=data
CORS_ORIGINS=http://127.0.0.1:8765,http://localhost:8765
```

Do **not** commit real credentials.  The `.env` file ships with the installer so end users do not need to configure anything.  Additional variables such as `APP_ENV` or `KIDUM_API_BASE_URL` can override environment-specific behaviour if required.

## Local Development

### Backend

```bash
pip install -r requirements.txt
python -m app.main
```

The server listens on `http://127.0.0.1:8765` and opens the default browser.

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

`VITE_API_BASE` controls which backend URL the frontend talks to (defaults to `http://127.0.0.1:8765`).

### Tests

Backend and service tests run with `pytest`.  Set dummy credentials to satisfy login checks:

```bash
export KIDUM_USERNAME=dummy
export KIDUM_PASSWORD=dummy
pytest
```

## Data Storage

All data remains on the local machine.  `DATA_ROOT` defaults to `data/` and contains per-course directories:

```
<DATA_ROOT>/courses/<teacher_id>/<course_id>/
    distance.db   # distance calculations
    messages.db   # fetched and edited messages
```

Databases are created on demand with WAL journaling for safe concurrent access.

## Packaging and Distribution

Build a self-contained installer for distribution:

```bash
pnpm --dir frontend build
pip install -r requirements.txt
pip install pyinstaller
sudo apt-get install -y makeself python3-dev  # or: brew install makeself
scripts/make_installer.sh
```

The script runs PyInstaller using `build/message_automation.spec` and wraps the output with `makeself`.  The resulting `installer/message_automation.run` file extracts the application and launches the backend which in turn opens the browser for the user.

## Troubleshooting

- Missing Python headers during packaging → install the appropriate `python3-dev` package.
- Avoid committing the `dist/` and `installer/` folders; they are generated during packaging.

## License

This project does not currently include an explicit license.


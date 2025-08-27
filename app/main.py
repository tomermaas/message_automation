from __future__ import annotations

import threading
import webbrowser

import uvicorn


def _open_browser() -> None:
    """Launch the default web browser to the local app URL."""
    webbrowser.open("http://127.0.0.1:8765")


if __name__ == "__main__":
    threading.Timer(1.0, _open_browser).start()
    uvicorn.run(
        "app.webapp:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        factory=False,
    )

"""
Background thread that runs the FastAPI/Uvicorn API server.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Callable, Optional


class ServerWorker:
    """Manages the embedded uvicorn API server in a daemon thread.

    The server runs in its own asyncio event loop (separate from Qt's loop)
    so that async providers work correctly.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        filter_mode: str = "all",
        on_log: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.filter_mode = filter_mode
        self._on_log = on_log
        self._server: Optional[object] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the API server in a background thread."""
        if self.is_running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="api-server", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the server to stop and wait for the thread to finish."""
        self._running = False
        if self._server is not None:
            # uvicorn.Server sets should_exit to stop the serve() coroutine
            self._server.should_exit = True
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        if self._on_log:
            self._on_log(msg)

    def _run(self) -> None:
        """Thread target: create a new event loop and run uvicorn.

        NOTE: This method imports the top-level ``main`` module to access the
        FastAPI ``app`` object and the ``_filter_mode`` global.  The repository
        root directory must be on ``sys.path`` (which is the case when the app
        is launched via ``app_entry.py`` from the project root).
        """
        try:
            import uvicorn
            import main as api_main

            # Inject settings into the API module's globals before the app starts
            api_main._filter_mode = self.filter_mode

            config = uvicorn.Config(
                api_main.app,
                host=self.host,
                port=self.port,
                log_level="warning",
                access_log=False,
            )
            self._server = uvicorn.Server(config)

            # Route uvicorn's log to our callback by monkey-patching its logger
            if self._on_log:
                import logging

                class _CallbackHandler(logging.Handler):
                    def __init__(self_, cb):
                        super().__init__()
                        self_._cb = cb

                    def emit(self_, record):
                        self_._cb(self_.format(record))

                uv_logger = logging.getLogger("uvicorn.access")
                uv_logger.addHandler(_CallbackHandler(self._on_log))

            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._server.serve())
        except Exception as exc:
            self._log(f"[server error] {exc}")
        finally:
            self._running = False

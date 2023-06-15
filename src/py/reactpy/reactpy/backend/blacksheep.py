from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable
from typing import Any, Callable

from blacksheep import (Application, Content, Response, WebSocket,
                        WebSocketDisconnectError)

from reactpy.backend._common import (ASSETS_PATH, CLIENT_BUILD_DIR,
                                     MODULES_PATH, STREAM_PATH, CommonOptions,
                                     read_client_index_html,
                                     serve_with_uvicorn)
from reactpy.backend.hooks import ConnectionContext
from reactpy.backend.hooks import use_connection as _use_connection
from reactpy.backend.types import Connection, Location
from reactpy.config import REACTPY_WEB_MODULES_DIR
from reactpy.core.layout import Layout
from reactpy.core.serve import RecvCoroutine, SendCoroutine, serve_layout
from reactpy.core.types import RootComponentConstructor

logger = logging.getLogger(__name__)


# BackendProtocol.Options
Options = CommonOptions


# BackendProtocol.configure
def configure(
    app: Application,
    component: RootComponentConstructor,
    options: Options | None = None,
) -> None:
    """Configure the necessary ReactPy routes on the given app.

    Parameters:
        app: An application instance
        component: A component constructor
        options: Options for configuring server behavior
    """
    options = options or Options()

    # this route should take priority so set up it up first
    _setup_single_view_dispatcher_route(app, component)

    _setup_common_routes(options, app)


# BackendProtocol.create_development_app
def create_development_app() -> Application:
    """Return a :class:`Application` app instance in debug mode"""
    return Application(debug=True, show_error_details=True)


# BackendProtocol.serve_development_app
async def serve_development_app(
    app: Application,
    host: str,
    port: int,
    started: asyncio.Event | None = None,
) -> None:
    """Run a development server for blacksheep"""
    await serve_with_uvicorn(app, host, port, started)


def use_websocket() -> WebSocket:
    """Get the current WebSocket object"""
    return use_connection().carrier


def use_connection() -> Connection[WebSocket]:
    conn = _use_connection()
    if not isinstance(conn.carrier, WebSocket):  # nocov
        msg = f"Connection has unexpected carrier {conn.carrier}. Are you running with a Flask server?"
        raise TypeError(msg)
    return conn


def _setup_common_routes(options: Options, app: Application) -> None:
    url_prefix = options.url_prefix

    app.serve_files(
        REACTPY_WEB_MODULES_DIR.current,
        root_path=str(MODULES_PATH),
    )
    app.serve_files(
        CLIENT_BUILD_DIR / "assets",
        root_path=str(ASSETS_PATH),
    )
    # register this last so it takes least priority
    index_html = bytes(read_client_index_html(options), encoding="utf-8")

    @app.router.get(f"{url_prefix}/")
    @app.router.get(url_prefix + "/{path:path}")
    async def serve_index() -> Response:
        return Response(200, content=Content(b"text/html", index_html))



def _setup_single_view_dispatcher_route(
    app: Application, component: RootComponentConstructor
) -> None:
    @app.router.ws(str(STREAM_PATH))
    @app.router.ws(f"{STREAM_PATH}/{{path:path}}")
    async def model_stream(socket: WebSocket) -> None:
        await socket.accept()
        send, recv = _make_send_recv_callbacks(socket)

        pathname = socket.scope["path"][len(str(STREAM_PATH)) :] or "/"
        search = socket.scope["query_string"].decode()

        try:
            await serve_layout(
                Layout(
                    ConnectionContext(
                        component(),
                        value=Connection(
                            scope=socket.scope,
                            location=Location(pathname, f"?{search}" if search else ""),
                            carrier=socket,
                        ),
                    )
                ),
                send,
                recv,
            )
        except WebSocketDisconnectError as error:
            logger.info(f"WebSocket disconnect: {error.code}")


def _make_send_recv_callbacks(
    socket: WebSocket,
) -> tuple[SendCoroutine, RecvCoroutine]:
    async def sock_send(value: Any) -> None:
        await socket.send_text(json.dumps(value))

    async def sock_recv() -> Any:
        return json.loads(await socket.receive_text())

    return sock_send, sock_recv

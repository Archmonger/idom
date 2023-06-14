from __future__ import annotations

from fastapi import FastAPI

from reactpy.backend import starlette

# BackendProtocol.Options
Options = starlette.Options

# BackendProtocol.configure
configure = starlette.configure


# BackendProtocol.create_development_app
def create_development_app() -> FastAPI:
    """Create a development ``FastAPI`` application instance."""
    return FastAPI(debug=True)


# BackendProtocol.serve_development_app
serve_development_app = starlette.serve_development_app

use_connection = starlette.use_connection

use_websocket = starlette.use_websocket

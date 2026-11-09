"""Serve Alfred branding independently of Chainlit's import-time APP_ROOT."""

from pathlib import Path

from starlette.requests import Request
from starlette.responses import FileResponse, Response


PUBLIC_DIR = Path(__file__).resolve().parent / "public"


class BrandingAssets:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        filename = None
        if scope["type"] == "http" and scope["method"] in ("GET", "HEAD"):
            if scope["path"] == "/favicon":
                filename = "alfred-signal.svg"
            elif scope["path"] == "/logo":
                theme = Request(scope).query_params.get("theme", "light")
                if theme in ("dark", "light"):
                    filename = "alfred-wordmark.svg"
        if filename is None:
            return await self.app(scope, receive, send)

        path = PUBLIC_DIR / filename
        if path.is_file():
            response = FileResponse(
                path,
                media_type="image/svg+xml",
                headers={"Cache-Control": "no-store"},
            )
        else:
            response = Response("Alfred branding asset missing", status_code=404)
        await response(scope, receive, send)


def install_branding(app):
    # Chainlit's watch mode reloads application modules, not the server app.
    if not getattr(app.state, "alfred_branding_installed", False):
        app.add_middleware(BrandingAssets)
        app.state.alfred_branding_installed = True

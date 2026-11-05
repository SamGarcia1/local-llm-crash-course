import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

import branding


class BrandingTests(unittest.TestCase):
    def test_explicit_assets_override_fallback_from_another_directory(self):
        async def fallback(request):
            return PlainTextResponse("original handler")

        app = Starlette(routes=[Route("/{path:path}", fallback)])
        branding.install_branding(app)
        branding.install_branding(app)
        self.assertEqual(len(app.user_middleware), 1)
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory) / "public"
            public.mkdir()
            for filename in ("favicon.png", "logo_dark.png", "logo_light.png"):
                (public / filename).write_bytes(b"\x89PNG\r\n\x1a\n" + filename.encode())
            previous = Path.cwd()
            try:
                other_directory = Path(directory) / "other"
                other_directory.mkdir()
                os.chdir(other_directory)
                with patch.object(branding, "PUBLIC_DIR", public), TestClient(app) as client:
                    for url, filename in (
                        ("/favicon", "favicon.png"),
                        ("/logo?theme=dark", "logo_dark.png"),
                        ("/logo?theme=light", "logo_light.png"),
                        ("/logo", "logo_light.png"),
                    ):
                        response = client.get(url)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.content, (public / filename).read_bytes())
                        self.assertEqual(response.headers["content-type"], "image/png")
                        self.assertEqual(response.headers["cache-control"], "no-store")
                    for url in ("/project/settings", "/logo?theme=invalid"):
                        self.assertEqual(client.get(url).text, "original handler")
                    (public / "favicon.png").unlink()
                    self.assertEqual(client.get("/favicon").status_code, 404)
            finally:
                os.chdir(previous)

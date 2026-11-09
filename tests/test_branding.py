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
            for filename in ("alfred-signal.svg", "alfred-wordmark.svg"):
                (public / filename).write_bytes(
                    f'<svg xmlns="http://www.w3.org/2000/svg"><title>{filename}</title></svg>'.encode()
                )
            previous = Path.cwd()
            try:
                other_directory = Path(directory) / "other"
                other_directory.mkdir()
                os.chdir(other_directory)
                with patch.object(branding, "PUBLIC_DIR", public), TestClient(app) as client:
                    for url, filename in (
                        ("/favicon", "alfred-signal.svg"),
                        ("/logo?theme=dark", "alfred-wordmark.svg"),
                        ("/logo?theme=light", "alfred-wordmark.svg"),
                        ("/logo", "alfred-wordmark.svg"),
                    ):
                        response = client.get(url)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.content, (public / filename).read_bytes())
                        self.assertEqual(
                            response.headers["content-type"],
                            "image/svg+xml",
                        )
                        self.assertEqual(response.headers["cache-control"], "no-store")
                    for url in ("/project/settings", "/logo?theme=invalid"):
                        self.assertEqual(client.get(url).text, "original handler")
                    (public / "alfred-signal.svg").unlink()
                    self.assertEqual(client.get("/favicon").status_code, 404)
            finally:
                os.chdir(previous)


class AvatarTests(unittest.IsolatedAsyncioTestCase):
    async def test_signal_registered_before_model_startup_even_when_unavailable(self):
        from unittest.mock import AsyncMock, Mock
        import langchain_app

        avatar = Mock(send=AsyncMock())
        message = Mock(send=AsyncMock())

        def unavailable():
            avatar.send.assert_awaited_once()
            raise RuntimeError("model unavailable")

        with (
            patch.object(langchain_app.cl, "Avatar", return_value=avatar) as create_avatar,
            patch.object(langchain_app.cl, "Message", return_value=message),
            patch.object(langchain_app.cl, "user_session") as session,
            patch.object(langchain_app, "build_llm_chain", side_effect=unavailable),
        ):
            await langchain_app.on_chat_start()
            create_avatar.assert_called_once_with(
                name="Alfred", url="/public/alfred-signal.svg"
            )
            session.set.assert_called_once_with("llm_chain", None)
            message.send.assert_awaited_once()


class BrandingAssetTests(unittest.TestCase):
    def test_real_assets_get_head_and_cache_headers(self):
        app = Starlette()
        branding.install_branding(app)
        with TestClient(app) as client:
            for url, filename in (
                ("/favicon", "alfred-signal.svg"),
                ("/logo?theme=dark", "alfred-wordmark.svg"),
                ("/logo?theme=light", "alfred-wordmark.svg"),
                ("/logo", "alfred-wordmark.svg"),
            ):
                with self.subTest(url=url):
                    response = client.get(url)
                    expected = (branding.PUBLIC_DIR / filename).read_bytes()
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers["content-type"], "image/svg+xml")
                    self.assertEqual(response.headers["cache-control"], "no-store")
                    self.assertEqual(response.content, expected)
                    head = client.head(url)
                    self.assertEqual(head.status_code, 200)
                    self.assertEqual(head.content, b"")
                    self.assertEqual(head.headers["content-type"], "image/svg+xml")
                    self.assertEqual(head.headers["cache-control"], "no-store")
                    self.assertEqual(int(head.headers["content-length"]), len(expected))
                    # Do not reuse a browser's previously cached logo/icon response.
                    conditional = client.get(
                        url, headers={"If-None-Match": response.headers["etag"]}
                    )
                    self.assertEqual(conditional.status_code, 200)
                    self.assertEqual(conditional.content, expected)

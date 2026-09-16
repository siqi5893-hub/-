import tempfile
import unittest
from pathlib import Path

from douyin_extractor.web import create_app


class FakeExtractor:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.calls = []

    def extract(self, request):
        self.calls.append(request)
        result = self.output_dir / "douyin_123.mp4"
        result.write_bytes(b"media")
        return result


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp.name)
        self.extractor = FakeExtractor(self.output_dir)

    def tearDown(self):
        self.temp.cleanup()

    def test_home_page_is_available(self):
        app = create_app(extractor=self.extractor)
        response = app.test_client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("抖音媒体提取", response.get_data(as_text=True))

    def test_rejects_unapproved_url(self):
        app = create_app(extractor=self.extractor)
        response = app.test_client().post(
            "/extract", data={"url": "https://example.com/x", "media_type": "video"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.extractor.calls, [])

    def test_requires_configured_app_token(self):
        app = create_app(extractor=self.extractor, app_token="secret")
        response = app.test_client().post(
            "/extract",
            data={
                "url": "https://v.douyin.com/abc123/",
                "media_type": "video",
                "token": "wrong",
            },
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.extractor.calls, [])

    def test_returns_extracted_file_as_attachment(self):
        app = create_app(extractor=self.extractor, app_token="secret")
        response = app.test_client().post(
            "/extract",
            data={
                "url": "https://v.douyin.com/abc123/",
                "media_type": "video",
                "token": "secret",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"media")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        response.close()


if __name__ == "__main__":
    unittest.main()

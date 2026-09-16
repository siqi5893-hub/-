import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from douyin_extractor.core import ExtractRequest, MediaExtractor, validate_media_url


class ValidateMediaUrlTests(unittest.TestCase):
    def test_accepts_douyin_share_and_video_urls(self):
        for url in (
            "https://v.douyin.com/abc123/",
            "https://www.douyin.com/video/123456",
            "https://www.iesdouyin.com/share/video/123456/",
        ):
            self.assertEqual(validate_media_url(url), url)

    def test_rejects_non_https_or_unapproved_hosts(self):
        for url in (
            "http://v.douyin.com/abc123/",
            "https://127.0.0.1/video/1",
            "https://douyin.com.evil.example/video/1",
            "file:///etc/passwd",
        ):
            with self.assertRaises(ValueError):
                validate_media_url(url)


class MediaExtractorTests(unittest.TestCase):
    def test_builds_video_command_without_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            extractor = MediaExtractor(output_dir=Path(directory), yt_dlp="yt-dlp")
            request = ExtractRequest("https://v.douyin.com/abc123/", "video")
            command = extractor.build_command(request)

        self.assertEqual(command[0], "yt-dlp")
        self.assertIn("--merge-output-format", command)
        self.assertEqual(command[-1], request.url)
        self.assertNotIn("shell=True", command)

    def test_audio_mode_requests_mp3(self):
        with tempfile.TemporaryDirectory() as directory:
            extractor = MediaExtractor(output_dir=Path(directory), yt_dlp="yt-dlp")
            command = extractor.build_command(
                ExtractRequest("https://v.douyin.com/abc123/", "audio")
            )

        self.assertIn("--extract-audio", command)
        self.assertIn("mp3", command)

    def test_cookie_file_is_optional_and_passed_as_one_argument(self):
        with tempfile.TemporaryDirectory() as directory:
            cookie = Path(directory) / "cookies.txt"
            cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
            extractor = MediaExtractor(
                output_dir=Path(directory), yt_dlp="yt-dlp", cookies=cookie
            )
            command = extractor.build_command(
                ExtractRequest("https://v.douyin.com/abc123/", "video")
            )

        index = command.index("--cookies")
        self.assertEqual(command[index + 1], str(cookie))

    @patch("douyin_extractor.core.shutil.which", return_value="/usr/bin/yt-dlp")
    @patch("douyin_extractor.core.subprocess.run")
    def test_extract_returns_only_new_media_file(self, run, _which):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            old_file = output_dir / "old.mp4"
            old_file.write_bytes(b"old")

            def create_result(*_args, **_kwargs):
                (output_dir / "douyin_123.mp4").write_bytes(b"new")

            run.side_effect = create_result
            extractor = MediaExtractor(output_dir=output_dir, yt_dlp="yt-dlp")
            result = extractor.extract(
                ExtractRequest("https://v.douyin.com/abc123/", "video")
            )

        self.assertEqual(result.name, "douyin_123.mp4")
        run.assert_called_once()
        self.assertNotIn("shell", run.call_args.kwargs)

    @patch("douyin_extractor.core.shutil.which", return_value="/usr/bin/yt-dlp")
    @patch("douyin_extractor.core.subprocess.run")
    def test_extract_uses_disposable_writable_cookie_copy(self, run, _which):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "output"
            output_dir.mkdir()
            source_cookie = Path(directory) / "cookies.txt"
            source_cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
            seen_cookie = None

            def inspect_command(command, **_kwargs):
                nonlocal seen_cookie
                seen_cookie = Path(command[command.index("--cookies") + 1])
                self.assertNotEqual(seen_cookie, source_cookie)
                self.assertTrue(seen_cookie.is_file())
                (output_dir / "douyin_123.mp4").write_bytes(b"new")

            run.side_effect = inspect_command
            extractor = MediaExtractor(output_dir=output_dir, cookies=source_cookie)
            extractor.extract(ExtractRequest("https://v.douyin.com/abc123/", "video"))

            self.assertIsNotNone(seen_cookie)
            self.assertFalse(seen_cookie.exists())


if __name__ == "__main__":
    unittest.main()

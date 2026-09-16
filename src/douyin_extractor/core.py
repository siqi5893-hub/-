from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


ALLOWED_HOSTS = {
    "douyin.com",
    "iesdouyin.com",
    "v.douyin.com",
    "www.douyin.com",
    "www.iesdouyin.com",
}
MEDIA_SUFFIXES = {"video": {".mp4", ".webm", ".mkv"}, "audio": {".mp3"}}


def validate_media_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url or len(url) > 2048:
        raise ValueError("链接为空或过长")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise ValueError("仅支持不含凭据的 HTTPS 链接")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if hostname not in ALLOWED_HOSTS:
        raise ValueError("目前仅支持抖音官方域名")
    if parsed.port not in (None, 443):
        raise ValueError("不支持自定义端口")
    return url


@dataclass(frozen=True)
class ExtractRequest:
    url: str
    media_type: str = "video"

    def __post_init__(self) -> None:
        validate_media_url(self.url)
        if self.media_type not in MEDIA_SUFFIXES:
            raise ValueError("media_type 必须是 video 或 audio")


class MediaExtractor:
    def __init__(
        self,
        output_dir: Path | str,
        yt_dlp: str = "yt-dlp",
        cookies: Path | str | None = None,
        timeout: int = 600,
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.yt_dlp = yt_dlp
        self.cookies = Path(cookies).resolve() if cookies else None
        self.timeout = timeout
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_command(
        self, request: ExtractRequest, cookie_path: Path | None = None
    ) -> list[str]:
        command = [
            self.yt_dlp,
            "--no-playlist",
            "--no-progress",
            "--restrict-filenames",
            "--output",
            str(self.output_dir / "douyin_%(id)s.%(ext)s"),
        ]
        selected_cookie = cookie_path or self.cookies
        if selected_cookie:
            if not selected_cookie.is_file():
                raise ValueError("Cookie 文件不存在")
            command.extend(["--cookies", str(selected_cookie)])
        if request.media_type == "video":
            command.extend(["--merge-output-format", "mp4"])
        else:
            command.extend(
                ["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"]
            )
        command.append(request.url)
        return command

    def extract(self, request: ExtractRequest) -> Path:
        if not shutil.which(self.yt_dlp) and not Path(self.yt_dlp).is_file():
            raise RuntimeError("找不到 yt-dlp，请先安装依赖")
        before = {p.resolve() for p in self.output_dir.iterdir() if p.is_file()}
        runtime_cookie = None
        try:
            if self.cookies:
                if not self.cookies.is_file():
                    raise ValueError("Cookie 文件不存在")
                with tempfile.NamedTemporaryFile(
                    prefix=".douyin-cookies-",
                    suffix=".txt",
                    dir=self.output_dir,
                    delete=False,
                ) as temporary:
                    runtime_cookie = Path(temporary.name)
                shutil.copyfile(self.cookies, runtime_cookie)
                runtime_cookie.chmod(0o600)
            subprocess.run(
                self.build_command(request, cookie_path=runtime_cookie),
                check=True,
                cwd=self.output_dir,
                timeout=self.timeout,
                stdin=subprocess.DEVNULL,
            )
        finally:
            if runtime_cookie:
                runtime_cookie.unlink(missing_ok=True)
        suffixes = MEDIA_SUFFIXES[request.media_type]
        created = [
            p.resolve()
            for p in self.output_dir.iterdir()
            if p.is_file() and p.resolve() not in before and p.suffix.lower() in suffixes
        ]
        if not created:
            candidates = [
                p.resolve()
                for p in self.output_dir.iterdir()
                if p.is_file() and p.suffix.lower() in suffixes
            ]
            if not candidates:
                raise RuntimeError("下载完成，但未找到媒体文件")
            return max(candidates, key=lambda p: p.stat().st_mtime_ns)
        return max(created, key=lambda p: p.stat().st_mtime_ns)


def extractor_from_env() -> MediaExtractor:
    return MediaExtractor(
        output_dir=os.getenv("OUTPUT_DIR", "downloads"),
        yt_dlp=os.getenv("YT_DLP", "yt-dlp"),
        cookies=os.getenv("DOUYIN_COOKIES") or None,
    )

from __future__ import annotations

import hmac
import os
import subprocess
import threading

from flask import Flask, Response, render_template, request, send_file

from .core import ExtractRequest, MediaExtractor, extractor_from_env


def create_app(
    extractor: MediaExtractor | None = None, app_token: str | None = None
) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024
    media_extractor = extractor or extractor_from_env()
    configured_token = app_token if app_token is not None else os.getenv("APP_TOKEN", "")
    extraction_lock = threading.Lock()

    @app.after_request
    def security_headers(response: Response) -> Response:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return render_template("index.html", token_required=bool(configured_token))

    @app.post("/extract")
    def extract():
        if configured_token and not hmac.compare_digest(
            request.form.get("token", ""), configured_token
        ):
            return render_template("error.html", message="访问令牌不正确"), 401
        try:
            job = ExtractRequest(
                url=request.form.get("url", ""),
                media_type=request.form.get("media_type", "video"),
            )
        except ValueError as exc:
            return render_template("error.html", message=str(exc)), 400
        if not extraction_lock.acquire(blocking=False):
            return render_template("error.html", message="已有任务正在运行，请稍后再试"), 429
        try:
            result = media_extractor.extract(job)
            return send_file(result, as_attachment=True, download_name=result.name)
        except (RuntimeError, subprocess.SubprocessError) as exc:
            app.logger.warning("media extraction failed: %s", type(exc).__name__)
            return render_template(
                "error.html", message="提取失败，请检查链接、Cookie 或网络后重试"
            ), 502
        finally:
            extraction_lock.release()

    return app


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8080"))
    if host not in {"127.0.0.1", "localhost", "::1"} and not os.getenv("APP_TOKEN"):
        raise SystemExit("公开监听前必须设置 APP_TOKEN")
    create_app().run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()

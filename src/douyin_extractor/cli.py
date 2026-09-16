from __future__ import annotations

import argparse
import sys

from .core import ExtractRequest, extractor_from_env


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="提取抖音视频或 MP3 音频")
    parser.add_argument("url", help="抖音分享链接")
    parser.add_argument(
        "--type", choices=("video", "audio"), default="video", dest="media_type"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = extractor_from_env().extract(
            ExtractRequest(url=args.url, media_type=args.media_type)
        )
    except Exception as exc:
        print(f"提取失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(result)


if __name__ == "__main__":
    main()

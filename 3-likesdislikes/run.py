"""Запуск рекомендательной системы ЛР3: python run.py [--port 8003] [--no-browser]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from recsys.service import DEFAULT_DATASET, RecommendationService  # noqa: E402
from recsys.web.api import create_app  # noqa: E402
from recsys.web.http import serve  # noqa: E402


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ЛР3: контентная рекомендательная система ликёров")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8003)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    return _with_browser_flag(parser).parse_args()


def _with_browser_flag(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--no-browser", action="store_true", help="не открывать браузер автоматически")
    return parser


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = arguments()
    service = RecommendationService.from_dataset(args.dataset)
    serve(create_app(service), args.host, args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()

"""Запуск объединённой системы ЛР4 + РК1: python run.py [--port 8004] [--no-browser]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bootstrap  # noqa: F401 — подключает модули ЛР3 из ../3-likesdislikes

from recsys.service import DEFAULT_DATASET, RecommendationService  # noqa: E402
from recsys.web.http import serve  # noqa: E402
from unified.api import create_app  # noqa: E402
from unified.service import UnifiedService  # noqa: E402


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ЛР4 + РК1: параметрический поиск и рекомендации ликёров")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8004)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    return _with_browser_flag(parser).parse_args()


def _with_browser_flag(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--no-browser", action="store_true", help="не открывать браузер автоматически")
    return parser


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = arguments()
    service = UnifiedService(RecommendationService.from_dataset(args.dataset))
    serve(create_app(service), args.host, args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()

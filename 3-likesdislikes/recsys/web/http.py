"""Минимальный веб-каркас на стандартной библиотеке: запрос, ответ, маршрутизатор, статика.

Внешние зависимости (Flask и т.п.) не нужны: интерфейс открывается в браузере,
сервер — `http.server.ThreadingHTTPServer`.
"""
from __future__ import annotations

import json
import mimetypes
import threading
import webbrowser
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import parse_qs, urlsplit

from ..recommend.types import ValidationError

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")


@dataclass(frozen=True)
class Request:
    """HTTP-запрос в удобном для обработчиков виде."""

    method: str
    path: str
    query: Mapping[str, list[str]] = field(default_factory=dict)
    body: bytes = b""
    cookies: Mapping[str, str] = field(default_factory=dict)

    def json(self) -> dict[str, Any]:
        try:
            data = json.loads(self.body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise HttpError(400, [f"тело запроса — не JSON: {error}"]) from error
        return data if isinstance(data, dict) else _not_object()


def _not_object() -> dict[str, Any]:
    raise HttpError(400, ["тело запроса должно быть JSON-объектом"])


@dataclass(frozen=True)
class Response:
    """HTTP-ответ: статус, тело, тип содержимого, дополнительные заголовки."""

    status: int
    body: bytes
    content_type: str = "application/json; charset=utf-8"
    headers: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def json(cls, data: Any, status: int = 200, headers: Mapping[str, str] | None = None) -> Response:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        return cls(status, body, headers=dict(headers or {}))


class HttpError(Exception):
    """Ошибка, которую нужно вернуть клиенту с указанным статусом."""

    def __init__(self, status: int, messages: Sequence[str]) -> None:
        super().__init__("; ".join(messages))
        self.status, self.messages = status, list(messages)


Handler = Callable[[Request], Response]


class Router:
    """Таблица маршрутов (метод, путь) → обработчик (паттерн Command)."""

    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], Handler] = {}

    def add(self, method: str, path: str, handler: Handler) -> Router:
        self._routes[(method.upper(), path)] = handler
        return self

    def find(self, request: Request) -> Handler | None:
        return self._routes.get((request.method, request.path))


class StaticFiles:
    """Раздача файлов интерфейса из нескольких каталогов (первый найденный побеждает)."""

    def __init__(self, roots: Sequence[Path]) -> None:
        self._roots = [Path(root).resolve() for root in roots]

    def response(self, path: str) -> Response | None:
        name = "index.html" if path in ("", "/") else path.lstrip("/")
        found = [root / name for root in self._roots if self._inside(root, root / name)]
        return self._file(found[0]) if found else None

    @staticmethod
    def _inside(root: Path, candidate: Path) -> bool:
        resolved = candidate.resolve()
        return resolved.is_file() and root in resolved.parents

    @staticmethod
    def _file(path: Path) -> Response:
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return Response(200, path.read_bytes(), f"{kind}; charset=utf-8", {"Cache-Control": "no-store"})


class Application:
    """Веб-приложение: API-маршруты, затем статика; ошибки превращаются в JSON."""

    def __init__(self, router: Router, static: StaticFiles) -> None:
        self._router, self._static = router, static

    def handle(self, request: Request) -> Response:
        try:
            return self._dispatch(request)
        except (HttpError, ValidationError) as error:
            return Response.json({"errors": error.messages}, getattr(error, "status", 400))

    def _dispatch(self, request: Request) -> Response:
        handler = self._router.find(request)
        static = self._static.response(request.path) if handler is None and request.method == "GET" else None
        if handler is None and static is None:
            raise HttpError(404, [f"не найдено: {request.method} {request.path}"])
        return handler(request) if handler else static


def parse_request(handler: BaseHTTPRequestHandler) -> Request:
    """Адаптер BaseHTTPRequestHandler → Request."""
    url, length = urlsplit(handler.path), int(handler.headers.get("Content-Length") or 0)
    cookies = {key: morsel.value for key, morsel in SimpleCookie(handler.headers.get("Cookie", "")).items()}
    body = handler.rfile.read(length) if length else b""
    return Request(handler.command, url.path, parse_qs(url.query), body, cookies)


def handler_class(app: Application) -> type[BaseHTTPRequestHandler]:
    """Класс-обработчик http.server, делегирующий всё приложению (паттерн Adapter)."""
    return type("AppRequestHandler", (_BaseHandler,), {"app": app})


class _BaseHandler(BaseHTTPRequestHandler):
    app: Application

    def do_GET(self) -> None:  # noqa: N802 — имя задано http.server
        self._send(self.app.handle(parse_request(self)))

    def do_POST(self) -> None:  # noqa: N802
        self._send(self.app.handle(parse_request(self)))

    def _send(self, response: Response) -> None:
        self.send_response(response.status)
        for name, value in {"Content-Type": response.content_type, **response.headers}.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(response.body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return None


def serve(app: Application, host: str, port: int, open_browser: bool = True) -> None:
    """Запуск сервера; по умолчанию сразу открывает интерфейс в браузере."""
    server, url = ThreadingHTTPServer((host, port), handler_class(app)), f"http://{host}:{port}/"
    print(f"Интерфейс: {url}  (Ctrl+C — остановить)")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    _forever(server)


def _forever(server: ThreadingHTTPServer) -> None:
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

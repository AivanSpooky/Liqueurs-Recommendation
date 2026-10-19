"""HTTP API объединённой системы. Каталог и справочники стратегий берутся из API ЛР3."""
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, Callable, Mapping

from recsys.web.api import STATIC_DIR as LR3_STATIC
from recsys.web.api import RecommendationApi
from recsys.web.http import Application, Request, Response, Router, StaticFiles

from . import presenter
from .service import UnifiedService
from .session import Session, SessionStore

STATIC_DIR = Path(__file__).resolve().parent / "static"
COOKIE = "liq_session"
Action = Callable[[Session, Mapping[str, Any]], None]


class UnifiedApi:
    """Маршруты: операции истории, отметки профиля, справочники; ответ — полное состояние сессии."""

    def __init__(self, service: UnifiedService, store: SessionStore) -> None:
        self._service, self._store = service, store
        self._lr3 = RecommendationApi(service.recsys)

    def routes(self, router: Router) -> Router:
        self._lr3.routes(router).add("GET", "/api/filters", self.filters).add("GET", "/api/state", self._stateful(_noop))
        for kind in ("search", "refine", "recommend"):
            router.add("POST", f"/api/{kind}", self._stateful(self._operation(kind)))
        actions = {"/api/profile": self._service.rate, "/api/history": _select, "/api/reset": _reset}
        return _register(router, {path: self._stateful(action) for path, action in actions.items()})

    def filters(self, request: Request) -> Response:
        return Response.json(self._service.filter_options())

    def _operation(self, kind: str) -> Action:
        return partial(self._run, kind)

    def _run(self, kind: str, session: Session, payload: Mapping[str, Any]) -> None:
        self._service.execute(session, kind, payload)

    def _stateful(self, action: Action) -> Callable[[Request], Response]:
        return lambda request: self._respond(request, action)

    def _respond(self, request: Request, action: Action) -> Response:
        key, session = self._store.resolve(request.cookies.get(COOKIE))
        action(session, request.json() if request.method == "POST" else {})
        cookie = {"Set-Cookie": f"{COOKIE}={key}; Path=/; HttpOnly; SameSite=Lax"}
        return Response.json(presenter.state(self._service.recsys.catalog, session), headers=cookie)


def _noop(session: Session, payload: Mapping[str, Any]) -> None:
    return None


def _select(session: Session, payload: Mapping[str, Any]) -> None:
    index = payload.get("index")
    session.history.select(index if isinstance(index, int) and not isinstance(index, bool) else -1)


def _reset(session: Session, payload: Mapping[str, Any]) -> None:
    session.reset(keep_profile=bool(payload.get("keep_profile", True)))


def _register(router: Router, handlers: Mapping[str, Callable[[Request], Response]]) -> Router:
    for path, handler in handlers.items():
        router.add("POST", path, handler)
    return router


def create_app(service: UnifiedService, store: SessionStore | None = None) -> Application:
    api = UnifiedApi(service, store or SessionStore())
    return Application(api.routes(Router()), StaticFiles([STATIC_DIR, LR3_STATIC]))

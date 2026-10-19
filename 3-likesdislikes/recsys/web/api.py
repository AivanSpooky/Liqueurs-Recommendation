"""HTTP API рекомендательной системы ЛР3."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from ..service import RecommendationService
from ..similarity.composite import WeightedSum
from . import presenter
from .http import Application, Request, Response, Router, StaticFiles

STATIC_DIR = Path(__file__).resolve().parent / "static"


class RecommendationApi:
    """Обработчики запросов: каталог, параметры стратегий, рекомендации."""

    def __init__(self, service: RecommendationService) -> None:
        self._service = service

    def routes(self, router: Router) -> Router:
        router.add("GET", "/api/catalog", self.catalog).add("GET", "/api/options", self.options)
        return router.add("POST", "/api/recommend", self.recommend)

    def catalog(self, request: Request) -> Response:
        items = [presenter.liqueur(item) for item in self._service.catalog]
        return Response.json({"items": items, "taxonomy": presenter.taxonomy(self._service.taxonomy.root)})

    def options(self, request: Request) -> Response:
        rec = self._service.recommender
        lists = {"rankers": presenter.strategies(rec.rankers), "policies": presenter.strategies(rec.policies)}
        return Response.json({**self._service.options(), **lists, "weights": self._weights()})

    def recommend(self, request: Request) -> Response:
        parsed = self._service.parse(request.json())
        results = [presenter.recommendation(rec) for rec in self._service.recommend(parsed)]
        return Response.json({"mode": parsed.mode.value, "results": results})

    def _weights(self) -> dict[str, Any]:
        measure = self._service.recommender.matrix.measure
        return measure.weights if isinstance(measure, WeightedSum) else {}


def create_app(service: RecommendationService, static_dirs: Sequence[Path] = (STATIC_DIR,)) -> Application:
    return Application(RecommendationApi(service).routes(Router()), StaticFiles(static_dirs))

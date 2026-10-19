"""Фасад ЛР3 для внешних клиентов (веб-интерфейс ЛР3 и объединённая система ЛР4)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .domain.catalog import Catalog, JsonCatalogLoader
from .domain.taxonomy import TasteTaxonomy
from .recommend.factory import DEFAULT_POLICY, DEFAULT_RANKER, build_recommender
from .recommend.recommender import ContentRecommender, Recommendation
from .recommend.requests import RequestParser, RequestValidator
from .recommend.types import Mode, RecommendRequest

DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "1-dataset" / "dataset.json"


class RecommendationService:
    """Паттерн Facade: каталог, таксономия и рекомендатель за одним простым интерфейсом."""

    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog
        self.taxonomy = TasteTaxonomy(catalog)
        self.recommender: ContentRecommender = build_recommender(catalog)
        self._parser = RequestParser()

    @classmethod
    def from_dataset(cls, path: Path = DEFAULT_DATASET) -> RecommendationService:
        return cls(JsonCatalogLoader(path).load())

    @property
    def validator(self) -> RequestValidator:
        return RequestValidator(self.catalog, self.recommender.rankers, self.recommender.policies)

    def parse(self, payload: Mapping[str, Any]) -> RecommendRequest:
        """JSON-запрос → проверенный RecommendRequest (иначе ValidationError)."""
        return self.validator.validate(self._parser.parse(payload))

    def recommend(self, request: RecommendRequest) -> list[Recommendation]:
        return self.recommender.recommend(request)

    def options(self) -> dict[str, Any]:
        modes = [{"key": mode.value, "title": mode.title} for mode in Mode]
        return {"modes": modes, "default_ranker": DEFAULT_RANKER, "default_policy": DEFAULT_POLICY}

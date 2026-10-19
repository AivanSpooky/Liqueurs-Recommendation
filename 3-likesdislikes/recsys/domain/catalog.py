"""Каталог ликёров (паттерн Repository) и загрузка из dataset.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable, Iterator, TypeVar

from .model import Liqueur, SugarClass, TastePath

T = TypeVar("T")

# Атрибут модели -> ключ записи в dataset.json (простые поля переносятся как есть).
_PLAIN_FIELDS = {
    "id": "id", "name": "name", "producer": "producer", "country": "country",
    "bitter": "bitter", "wood_contact": "wood_contact",
    "abv": "abv_pct", "sugar": "sugar_gpl", "volume": "volume_l",
}
_TASTE_FIELDS = {"l1": "l1", "l2": "l2", "l3": "l3", "code": "id_path"}


class Catalog:
    """Неизменяемое хранилище объектов с доступом по идентификатору."""

    def __init__(self, items: Iterable[Liqueur]) -> None:
        self._items = {item.id: item for item in items}

    def __iter__(self) -> Iterator[Liqueur]:
        return iter(self._items.values())

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item_id: object) -> bool:
        return item_id in self._items

    def get(self, item_id: str) -> Liqueur:
        if item_id not in self._items:
            raise KeyError(f"в каталоге нет объекта {item_id!r}")
        return self._items[item_id]

    def ids(self) -> list[str]:
        return list(self._items)

    def distinct(self, getter: Callable[[Liqueur], T]) -> list[T]:
        """Уникальные значения признака в порядке первого появления."""
        return list(dict.fromkeys(getter(item) for item in self))


class JsonCatalogLoader:
    """Читает dataset.json (ЛР1) и строит объекты доменной модели."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def load(self) -> Catalog:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return Catalog(self.to_liqueur(record) for record in data["records"])

    @staticmethod
    def to_liqueur(record: dict) -> Liqueur:
        plain = {attr: record[key] for attr, key in _PLAIN_FIELDS.items()}
        taste = TastePath(**{attr: record["taste"][key] for attr, key in _TASTE_FIELDS.items()})
        sugar_class = SugarClass.from_label(record["sugar_class"])
        return Liqueur(**plain, taste=taste, sugar_class=sugar_class, notes=record.get("notes", ""))

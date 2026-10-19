"""Доменная модель: ликёр и его признаки (структура зафиксирована в ЛР1)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import takewhile

TASTE_DEPTH = 3


class SugarClass(Enum):
    """Порядковая лингвистическая переменная «класс сладости» по sugar_gpl."""

    LOW = ("малосладкий", 0)
    MEDIUM = ("умеренный", 1)
    SWEET = ("сладкий", 2)
    CREME = ("crème", 3)

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def rank(self) -> int:
        return self.value[1]

    @classmethod
    def from_label(cls, label: str) -> SugarClass:
        matches = [member for member in cls if member.label == label]
        if not matches:
            raise ValueError(f"неизвестный класс сладости: {label!r}")
        return matches[0]


@dataclass(frozen=True)
class TastePath:
    """Путь листа в таксономии вкуса: L1 / L2 / L3 (корень дерева — «Ликёры»)."""

    l1: str
    l2: str
    l3: str
    code: str

    @property
    def levels(self) -> tuple[str, str, str]:
        return (self.l1, self.l2, self.l3)

    def prefix(self, depth: int) -> tuple[str, ...]:
        return self.levels[:depth]

    def common_depth(self, other: TastePath | tuple[str, ...]) -> int:
        """Глубина наименьшего общего предка (LCA); 0 — общий только корень."""
        others = other.levels if isinstance(other, TastePath) else other
        return sum(1 for _ in takewhile(lambda pair: pair[0] == pair[1], zip(self.levels, others)))


@dataclass(frozen=True)
class Liqueur:
    """Объект рекомендации. Признаки: см. отчёт, раздел ЛР1."""

    id: str
    name: str
    producer: str
    country: str
    bitter: bool
    wood_contact: bool
    abv: float
    sugar: float
    volume: float
    taste: TastePath
    sugar_class: SugarClass
    notes: str = ""

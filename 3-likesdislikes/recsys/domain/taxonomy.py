"""Дерево таксономии вкуса, восстановленное по листьям объектов каталога."""
from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import Catalog
from .model import TASTE_DEPTH

ROOT_LABEL = "Ликёры"


@dataclass
class TaxonomyNode:
    """Узел дерева: путь от корня, дочерние узлы, объекты листа."""

    path: tuple[str, ...]
    children: dict[str, TaxonomyNode] = field(default_factory=dict)
    items: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.path[-1] if self.path else ROOT_LABEL

    def child(self, label: str) -> TaxonomyNode:
        return self.children.setdefault(label, TaxonomyNode(self.path + (label,)))

    def walk(self) -> list[TaxonomyNode]:
        """Все узлы поддерева в порядке обхода в глубину (корень первым)."""
        return [self] + [node for child in self.children.values() for node in child.walk()]

    def item_ids(self) -> list[str]:
        return self.items + [i for child in self.children.values() for i in child.item_ids()]


class TasteTaxonomy:
    """Иерархия «Ликёры → L1 → L2 → L3» (ЛР1)."""

    def __init__(self, catalog: Catalog) -> None:
        self.root = TaxonomyNode(())
        for item in catalog:
            self._leaf(item.taste.levels).items.append(item.id)

    def _leaf(self, levels: tuple[str, ...]) -> TaxonomyNode:
        node = self.root
        for label in levels:
            node = node.child(label)
        return node

    def find(self, path: tuple[str, ...]) -> TaxonomyNode | None:
        nodes = {node.path: node for node in self.root.walk()}
        return nodes.get(tuple(path))

    def height(self) -> int:
        return TASTE_DEPTH

    def size(self) -> int:
        return len(self.root.walk())

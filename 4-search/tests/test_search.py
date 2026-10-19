"""Фильтры, разбор запроса и поисковая система ЛР4."""
import unittest

from tests.support import unified  # noqa: I001 — первым: подключает модули ЛР3

from recsys.recommend.types import ValidationError
from search.engine import SearchEngine
from search.filters import TasteFilter, TextFilter
from search.query import QueryParser

CATALOG = unified().recsys.catalog


def found(payload: dict) -> list[str]:
    result = SearchEngine(CATALOG).search(QueryParser(CATALOG).parse(payload))
    return [hit.item.id for hit in result.hits] if result.exact else []


class FilterTest(unittest.TestCase):
    def test_taste_degree_follows_taxonomy(self) -> None:
        amaro = TasteFilter((("Травяные", "Смесь трав", "Амаро"),))
        self.assertEqual([round(amaro.degree(CATALOG.get(i)), 3) for i in ("L05", "L03", "L01", "L08")],
                         [1.0, 0.667, 0.333, 0.0])

    def test_text_ignores_case_accents_and_small_typos(self) -> None:
        self.assertTrue(TextFilter("KAHLUA").matches(CATALOG.get("L25")))
        self.assertGreater(TextFilter("kalua").degree(CATALOG.get("L25")), 0.7)


class QueryTest(unittest.TestCase):
    def test_combined_filters(self) -> None:
        self.assertEqual(found({"taste": [["Травяные"]], "countries": ["Италия"], "abv": {"min": "20", "max": "30"}}), ["L05", "L07"])

    def test_empty_query_returns_everything(self) -> None:
        self.assertEqual(len(found({})), 30)

    def test_all_field_errors_are_reported(self) -> None:
        payload = {"abv": {"min": "x"}, "sugar": {"min": 50, "max": 10}, "bitter": "maybe", "countries": ["Марс"]}
        with self.assertRaises(ValidationError) as context:
            QueryParser(CATALOG).parse(payload)
        self.assertEqual(len(context.exception.messages), 4)


class FallbackTest(unittest.TestCase):
    def test_not_found_gives_message_suggestions_and_advice(self) -> None:
        query = QueryParser(CATALOG).parse({"taste": [["Обжаренные", "Кофейные"]], "abv": {"max": 15}, "bitter": "yes"})
        result = SearchEngine(CATALOG).search(query)
        self.assertFalse(result.exact)
        self.assertEqual([h.item.id for h in result.hits[:2]], ["L25", "L24"])
        self.assertTrue(result.advice and result.advice.found >= 1)


if __name__ == "__main__":
    unittest.main()

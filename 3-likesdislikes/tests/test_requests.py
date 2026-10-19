"""Проверка корректности ввода: все ошибки собираются и возвращаются пользователю."""
import unittest

from recsys.recommend import ValidationError
from tests.support import service


def errors(payload: dict) -> list[str]:
    try:
        service().parse(payload)
    except ValidationError as error:
        return error.messages
    return []


class ParserTest(unittest.TestCase):
    def test_type_errors_are_collected_together(self) -> None:
        self.assertEqual(len(errors({"mode": "v9", "likes": "L01", "top_n": "abc"})), 3)

    def test_valid_request(self) -> None:
        self.assertEqual(errors({"mode": "v2", "likes": ["L01", "L02"], "top_n": "5"}), [])


class RulesTest(unittest.TestCase):
    def test_unknown_and_overlapping_ids(self) -> None:
        messages = errors({"mode": "v3", "likes": ["L01", "X1"], "dislikes": ["L01"]})
        self.assertTrue(any("X1" in m for m in messages) and any("одновременно" in m for m in messages))

    def test_seed_mode_needs_exactly_one_item(self) -> None:
        self.assertTrue(errors({"mode": "v1", "likes": ["L01", "L02"]}))
        self.assertTrue(errors({"mode": "v1", "likes": []}))

    def test_dislikes_only_allowed_in_v3(self) -> None:
        self.assertTrue(errors({"mode": "v2", "likes": ["L01"], "dislikes": ["L02"]}))
        self.assertEqual(errors({"mode": "v3", "dislikes": ["L02"]}), [])

    def test_top_n_bounds_and_unknown_strategy(self) -> None:
        self.assertTrue(errors({"mode": "v2", "likes": ["L01"], "top_n": 0}))
        self.assertTrue(errors({"mode": "v2", "likes": ["L01"], "ranker": "magic"}))

    def test_nothing_left_to_recommend(self) -> None:
        self.assertTrue(errors({"mode": "v3", "likes": ["L01"], "pool": ["L01"]}))


if __name__ == "__main__":
    unittest.main()

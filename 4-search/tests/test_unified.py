"""Объединённая система: цикл поиск → рекомендации → уточнение, история и сессии."""
import json
import unittest

from tests.support import unified  # noqa: I001 — первым: подключает модули ЛР3

from recsys.recommend.types import ValidationError
from recsys.web.http import Request
from unified.api import COOKIE, create_app
from unified.session import Session


class FlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.session, self.service = Session(), unified()

    def run_step(self, kind: str, payload: dict):
        return self.service.execute(self.session, kind, payload)

    def rate(self, *marks: tuple[str, str]) -> None:
        for action, item in marks:
            self.service.rate(self.session, {"action": action, "id": item})

    def test_search_recommend_refine_cycle(self) -> None:
        self.run_step("search", {"filters": {"taste": [["Травяные"]]}})
        self.rate(("like", "L05"), ("like", "L03"), ("dislike", "L06"))
        recommended = self.run_step("recommend", {"top_n": 5})
        refined = self.run_step("refine", {"filters": {"abv": {"min": 30}}})
        self.assertTrue(set(refined.ids()) <= set(recommended.ids()) and refined.parent == recommended.index)

    def test_recommendations_can_be_filtered_and_scoped(self) -> None:
        self.service.rate(self.session, {"action": "like", "id": "L08"})
        step = self.run_step("recommend", {"top_n": 3, "use_filters": True, "filters": {"countries": ["Италия"]}})
        self.assertTrue(all(unified().recsys.catalog.get(i).country == "Италия" for i in step.ids()))

    def test_history_select_and_refine_from_old_step(self) -> None:
        first = self.run_step("search", {"filters": {"taste": [["Фруктовые"]]}})
        self.run_step("search", {"filters": {"taste": [["Ореховые"]]}})
        self.session.history.select(first.index)
        self.assertEqual(self.run_step("refine", {"filters": {"countries": ["Франция"]}}).parent, first.index)

    def test_refine_without_history_is_an_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.run_step("refine", {"filters": {}})


class ApiTest(unittest.TestCase):
    def test_session_cookie_keeps_profile(self) -> None:
        app = create_app(unified())
        first = app.handle(Request("POST", "/api/profile", body=json.dumps({"action": "like", "id": "L01"}).encode()))
        key = first.headers["Set-Cookie"].split(";")[0].split("=")[1]
        state = json.loads(app.handle(Request("GET", "/api/state", cookies={COOKIE: key})).body)
        self.assertEqual(state["profile"]["likes"], ["L01"])

    def test_bad_input_is_400(self) -> None:
        response = create_app(unified()).handle(Request("POST", "/api/search", body=b'{"filters": {"abv": {"min": "x"}}}'))
        self.assertEqual(response.status, 400)


if __name__ == "__main__":
    unittest.main()

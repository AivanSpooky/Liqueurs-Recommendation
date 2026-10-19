"""HTTP-слой без сети: маршрутизация, статика, преобразование ошибок в JSON 400/404."""
import json
import unittest

from recsys.web.api import create_app
from recsys.web.http import Request
from tests.support import service


def call(method: str, path: str, payload=None):
    body = json.dumps(payload).encode() if payload is not None else b""
    response = create_app(service()).handle(Request(method, path, body=body))
    return response.status, response.body


class WebTest(unittest.TestCase):
    def test_catalog_and_index(self) -> None:
        self.assertEqual(len(json.loads(call("GET", "/api/catalog")[1])["items"]), 30)
        self.assertIn(b"<!doctype html>", call("GET", "/")[1])

    def test_recommend_ok(self) -> None:
        status, body = call("POST", "/api/recommend", {"mode": "v1", "likes": ["L26"], "top_n": 1})
        self.assertEqual((status, json.loads(body)["results"][0]["item"]["id"]), (200, "L27"))

    def test_validation_error_is_400(self) -> None:
        status, body = call("POST", "/api/recommend", {"mode": "v1"})
        self.assertEqual(status, 400)
        self.assertTrue(json.loads(body)["errors"])

    def test_unknown_path_and_traversal_are_404(self) -> None:
        self.assertEqual(call("GET", "/nope")[0], 404)
        self.assertEqual(call("GET", "/../service.py")[0], 404)


if __name__ == "__main__":
    unittest.main()

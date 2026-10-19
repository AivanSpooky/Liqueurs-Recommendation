"""Стратегии ПСВ1–ПСВ3: ожидаемое поведение на контрольных сценариях."""
import unittest

from recsys.recommend import Mode, RecommendRequest, UserProfile
from tests.support import service


def top(mode: Mode, likes=(), dislikes=(), n=5, **options) -> list[str]:
    request = RecommendRequest(mode, UserProfile(tuple(likes), tuple(dislikes)), n, **options)
    return [rec.item.id for rec in service().recommend(request)]


class SeedTest(unittest.TestCase):
    def test_v1_ranks_by_similarity_to_seed(self) -> None:
        self.assertEqual(top(Mode.SEED, ["L26"], n=1), ["L27"])
        self.assertEqual(top(Mode.SEED, ["L05"], n=2), ["L07", "L06"])

    def test_seed_is_not_recommended(self) -> None:
        self.assertNotIn("L05", top(Mode.SEED, ["L05"], n=29))


class LikesTest(unittest.TestCase):
    def test_group_ranker_serves_every_interest(self) -> None:
        items = top(Mode.LIKES, ["L05", "L28"], n=4, ranker="group")
        self.assertEqual(set(items[:2]), {"L07", "L29"})

    def test_max_ranker_lets_one_interest_dominate(self) -> None:
        items = top(Mode.LIKES, ["L05", "L28"], n=4, ranker="max")
        self.assertEqual(items[:2], ["L07", "L06"])

    def test_all_rankers_return_n_unique_items(self) -> None:
        for ranker in service().recommender.rankers:
            items = top(Mode.LIKES, ["L05", "L28", "L08"], n=7, ranker=ranker)
            self.assertEqual(len(set(items)), 7, ranker)


class DislikesTest(unittest.TestCase):
    LIKES, DISLIKE = ["L03", "L05", "L07"], ["L06"]

    def test_contrastive_keeps_the_liked_genre(self) -> None:
        items = top(Mode.FULL, self.LIKES, self.DISLIKE, policy="contrastive")
        self.assertIn("L04", items)

    def test_subtractive_spoils_the_liked_genre(self) -> None:
        items = top(Mode.FULL, self.LIKES, self.DISLIKE, policy="subtract")
        self.assertNotIn("L04", items)

    def test_threshold_excludes_similar_items(self) -> None:
        items = top(Mode.FULL, ["L08"], ["L09"], n=29, policy="threshold")
        self.assertTrue(all(service().recommender.matrix.get(i, "L09") < 0.7 for i in items))

    def test_only_dislikes_moves_away(self) -> None:
        items = top(Mode.FULL, [], ["L06"], n=3)
        self.assertTrue(all(service().catalog.get(i).taste.l1 != "Травяные" for i in items))


if __name__ == "__main__":
    unittest.main()

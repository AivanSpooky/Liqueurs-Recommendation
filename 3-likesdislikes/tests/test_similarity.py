"""Мера близости ЛР3 совпадает с итоговой мерой ЛР2 и обладает свойствами близости."""
import csv
import unittest

from tests.support import ROOT, service

LR2_MATRIX = ROOT.parent / "2-metrics" / "out" / "matrices" / "agg_total_sim.csv"


def lr2_values() -> dict[tuple[str, str], float]:
    with open(LR2_MATRIX, encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle, delimiter=";"))
    ids = rows[0][1:]
    return {(row[0].split()[0], ids[j]): float(v.replace(",", ".")) for row in rows[1:] for j, v in enumerate(row[1:])}


class SimilarityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix, self.ids = service().recommender.matrix, service().catalog.ids()

    def test_matches_lr2_matrix(self) -> None:
        for (a, b), expected in lr2_values().items():
            self.assertAlmostEqual(self.matrix.get(a, b), expected, places=3)

    def test_identity_and_symmetry(self) -> None:
        for a in self.ids:
            self.assertAlmostEqual(self.matrix.get(a, a), 1.0)
            self.assertTrue(all(abs(self.matrix.get(a, b) - self.matrix.get(b, a)) < 1e-12 for b in self.ids))

    def test_range(self) -> None:
        values = [self.matrix.get(a, b) for a in self.ids for b in self.ids]
        self.assertTrue(all(0.0 <= v <= 1.0 + 1e-12 for v in values))

    def test_weights_sum_to_one(self) -> None:
        self.assertAlmostEqual(sum(self.matrix.measure.weights.values()), 1.0)


if __name__ == "__main__":
    unittest.main()

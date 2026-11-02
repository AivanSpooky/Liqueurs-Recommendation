"""Требования ЛР5 к корпусу: 6 классов, не меньше 5 вопросов в классе, 2–3 переформулировки."""
import json
import unittest

from tests.support import DATA, ROOT, corpus

CLASSES = ["domain", "abilities", "recommend", "compare", "modify", "refuse"]


class CorpusTest(unittest.TestCase):
    def test_six_classes_with_five_questions(self) -> None:
        self.assertEqual([c["key"] for c in corpus().classes], CLASSES)
        self.assertTrue(all(len(c["questions"]) >= 5 for c in corpus().classes))

    def test_every_question_has_rephrasings(self) -> None:
        questions = [q for c in corpus().classes for q in c["questions"]]
        self.assertTrue(all(len(q["paraphrases"]) >= 2 for q in questions))

    def test_texts_and_ids_are_unique(self) -> None:
        texts = [s.text for s in corpus().samples()]
        self.assertEqual(len(texts), len(set(texts)))

    def test_cocktail_questions_are_present(self) -> None:
        texts = " ".join(s.text.lower() for s in corpus().samples())
        self.assertTrue(all(word in texts for word in ("коктейл", "смешать", "маргарит", "кофе")))


def load(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class KnowledgeTest(unittest.TestCase):
    def test_lexicon_and_cocktails_refer_to_dataset(self) -> None:
        ids = {record["id"] for record in load(ROOT.parent / "1-dataset" / "dataset.json")["records"]}
        cocktails = load(DATA / "cocktails.json")
        self.assertEqual(set(load(DATA / "lexicon.json")["liqueur"]), ids)
        self.assertTrue(all(set(c["liqueurs"]) <= ids for c in cocktails["cocktails"]))
        self.assertTrue(set(cocktails["mixers"]) <= ids)


if __name__ == "__main__":
    unittest.main()

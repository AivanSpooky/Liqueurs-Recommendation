"""Опорные слова разделяют классы: исходные вопросы — без ошибок, переформулировки — почти без ошибок."""
import unittest

from dialogue.corpus import ORIGINAL, PARAPHRASE
from dialogue.lexicon import Lexicon
from dialogue.refusal import RefusalTemplates
from dialogue.rules import Utterance
from dialogue.text import normalize
from tests.support import DATA, classifier, corpus


def accuracy(kind: str) -> float:
    samples = [s for s in corpus().samples() if s.kind == kind]
    return sum(classifier().classify(s.text).key == s.label for s in samples) / len(samples)


class NormalizeTest(unittest.TestCase):
    def test_case_accents_and_yo(self) -> None:
        self.assertEqual(normalize("Kahlúa, ЁЛКА — Б-52!"), "kahlua елка б-52")
        self.assertEqual(normalize("Какой"), "какой")


class ClassifierTest(unittest.TestCase):
    def test_original_questions(self) -> None:
        self.assertEqual(accuracy(ORIGINAL), 1.0)

    def test_paraphrases(self) -> None:
        self.assertGreaterEqual(accuracy(PARAPHRASE), 0.95)

    def test_two_liqueurs_mean_comparison(self) -> None:
        self.assertEqual(classifier().classify("Baileys или Amarula?").key, "compare")

    def test_no_keywords_means_polite_refusal(self) -> None:
        self.assertEqual(classifier().classify("Кто написал «Войну и мир»?").key, "refuse")


class RefusalTest(unittest.TestCase):
    def kind(self, text: str) -> str:
        utterance = Utterance.parse(text, Lexicon.load(DATA / "lexicon.json"))
        return RefusalTemplates.load(DATA / "refusals.json").kind(utterance).key

    def test_reason_is_chosen_by_keywords(self) -> None:
        cases = {"Сколько стоит Baileys?": "shop", "Какая завтра погода?": "offtopic",
                 "Сколько можно выпить?": "health", "Какой ликёр пил Хемингуэй?": "unknown"}
        self.assertEqual({text: self.kind(text) for text in cases}, cases)


if __name__ == "__main__":
    unittest.main()

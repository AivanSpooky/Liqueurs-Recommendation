"""Меры близости ЛР2 в объектном виде: частные меры, итоговая мера, матрица смежности."""
from .composite import Component, WeightedSum
from .factory import EXPERT_WEIGHTS, MeasureFactory
from .matrix import SimilarityMatrix
from .measures import (
    ExactMatch, NormalizedEuclidean, NumericAxis, OrdinalSimilarity,
    SimilarityMeasure, SimpleMatching, WuPalmer,
)

__all__ = [
    "Component", "WeightedSum", "EXPERT_WEIGHTS", "MeasureFactory", "SimilarityMatrix",
    "ExactMatch", "NormalizedEuclidean", "NumericAxis", "OrdinalSimilarity",
    "SimilarityMeasure", "SimpleMatching", "WuPalmer",
]

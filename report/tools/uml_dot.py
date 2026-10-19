"""Генерация UML-диаграмм классов (diags/cls_*.dot) для отчёта. Рендер: dot -Tpng."""
from pathlib import Path

DIAGS = Path(__file__).resolve().parents[1] / "diags"
HEAD = '''digraph G {
rankdir=BT; nodesep=0.35; ranksep=0.55; fontname="DejaVu Sans";
node [fontname="DejaVu Sans", fontsize=10, shape=plain];
edge [fontname="DejaVu Sans", fontsize=9, color="#5b4f47"];
'''
IF, EXT = "#f7ead9", "#e9f0fa"


def cls(name, methods=(), stereo="", fill="#ffffff"):
    rows = "".join(f'<tr><td align="left" balign="left">{m}</td></tr>' for m in methods)
    st = f'<tr><td><font point-size="8">«{stereo}»</font></td></tr>' if stereo else ""
    body = f'<tr><td><table border="0" cellspacing="0" cellpadding="1">{rows}</table></td></tr>' if methods else ""
    return (f'"{name}" [label=<<table border="1" cellborder="0" cellspacing="0" cellpadding="4" '
            f'color="#7a1f3d" bgcolor="{fill}">{st}<tr><td><b>{name}</b></td></tr>{body}</table>>];')


def inh(a, b):
    return f'"{a}" -> "{b}" [arrowhead=onormal];'


def use(a, b, label=""):
    return f'"{a}" -> "{b}" [arrowhead=vee, style=dashed, label="{label}"];'


def agg(a, b, label=""):
    return f'"{a}" -> "{b}" [arrowhead=vee, arrowtail=odiamond, dir=both, label="{label}"];'


def write(name, items):
    (DIAGS / f"cls_{name}.dot").write_text(HEAD + "\n".join(items) + "\n}\n", encoding="utf-8")


SIMILARITY = [
    cls("SimilarityMeasure", ["similarity(a, b): float"], "interface", IF),
    cls("NormalizedEuclidean", ["axes: NumericAxis[3]"]), cls("SimpleMatching", ["getters"]), cls("WuPalmer"),
    cls("OrdinalSimilarity", ["getter, levels"]), cls("ExactMatch", ["name, getter"]),
    cls("WeightedSum", ["weights", "contributions(a, b)"], "composite"),
    cls("MeasureFactory", ["expert(): WeightedSum", "partial_measures()"], "factory"),
    cls("SimilarityMatrix", ["get(a, b)", "best(x, anchors)"], "proxy / cache"),
    cls("Catalog", ["get(id)", "ids()", "distinct(getter)"], "repository"), cls("JsonCatalogLoader", ["load(): Catalog"]),
    *[inh(c, "SimilarityMeasure") for c in ("NormalizedEuclidean", "SimpleMatching", "WuPalmer", "OrdinalSimilarity",
                                            "ExactMatch", "WeightedSum")],
    agg("WeightedSum", "SimilarityMeasure", "Component (ω_k) ×6"), use("MeasureFactory", "WeightedSum", "создаёт"),
    use("SimilarityMatrix", "SimilarityMeasure", "кэширует"), use("SimilarityMatrix", "Catalog"),
    use("JsonCatalogLoader", "Catalog", "создаёт"), use("MeasureFactory", "Catalog", "min-max"),
]
RANKERS = [
    cls("LikesRanker", ["rank(likes, candidates, adjust)"], "strategy", IF),
    cls("WeightedMeanRanker", ["weights(likes)"], "template method"),
    cls("MeanRanker", ["А"]), cls("RecencyRanker", ["Б: γ = 0,7"]), cls("BalancedRanker", ["В: 1/|группа|"]),
    cls("MaxRanker"), cls("RoundRobinRanker", ["Г′"]), cls("GroupRanker", ["Г: θ = 0,65"]),
    cls("AvoidRanker", ["только дизлайки"]), cls("LikeGrouper", ["groups(likes)"]),
    *[inh(c, "LikesRanker") for c in ("WeightedMeanRanker", "MaxRanker", "RoundRobinRanker", "GroupRanker", "AvoidRanker")],
    *[inh(c, "WeightedMeanRanker") for c in ("MeanRanker", "RecencyRanker", "BalancedRanker")],
    use("GroupRanker", "LikeGrouper"), use("BalancedRanker", "LikeGrouper"),
]
CORE = [
    cls("DislikePolicy", ["adjuster(profile)", "adjust(scored, profile)"], "strategy", IF),
    cls("ExcludeOnly", ["1"]), cls("ThresholdExclusion", ["2: τ = 0,7"]), cls("SubtractivePenalty", ["3: β"]),
    cls("ContrastivePenalty", ["4: β = 1"]), cls("LikesRanker", [], "strategy", IF), cls("SimilarityMatrix"),
    cls("ContentRecommender", ["recommend(request)", "rank(request)", "candidates(request)"], "facade"),
    cls("RequestParser", ["parse(json)"]), cls("RequestValidator", ["validate(request)", "правил: 7"]),
    cls("RecommendationService", ["parse(json)", "recommend(request)", "catalog, taxonomy"], "facade"),
    *[inh(c, "DislikePolicy") for c in ("ExcludeOnly", "ThresholdExclusion", "SubtractivePenalty", "ContrastivePenalty")],
    agg("ContentRecommender", "LikesRanker", "реестр"), agg("ContentRecommender", "DislikePolicy", "реестр"),
    use("ContentRecommender", "SimilarityMatrix"), agg("RecommendationService", "ContentRecommender"),
    use("RecommendationService", "RequestParser"), use("RecommendationService", "RequestValidator"),
]
SEARCH = [
    cls("Filter", ["degree(x): [0,1]", "matches(x)", "describe()", "relaxed(): Filter?"], "specification", IF),
    cls("RangeFilter", ["low, high, span"]), cls("ChoiceFilter", ["allowed"]), cls("FlagFilter", ["expected"]),
    cls("TasteFilter", ["nodes"]), cls("SugarClassFilter", ["allowed"]), cls("TextFilter", ["needle"]),
    cls("SearchQuery", ["matches(x)", "utility(x)", "unmet(x)"], "AND-композиция"),
    cls("QueryParser", ["parse(json): SearchQuery"], "builder"),
    cls("UtilityFunction", ["score(query, x, r)"]), cls("RelaxationAdvisor", ["advise(query, items)"]),
    cls("SearchEngine", ["search(query, pool, relevance)"]),
    cls("Command", ["execute(session, payload)", "step(...)"], "command", IF),
    cls("SearchCommand"), cls("RefineCommand"), cls("RecommendCommand"),
    cls("Session", ["profile", "rate(kind, id)", "reset()"]), cls("History", ["push(step)", "select(i)", "current"], "caretaker"),
    cls("Step", ["kind, title, rows", "filters, settings"], "memento"),
    cls("UnifiedService", ["execute(session, kind, json)", "rate(...)"], "facade"),
    cls("RecommendationService", [], "ЛР3", EXT),
    *[inh(c, "Filter") for c in ("RangeFilter", "ChoiceFilter", "FlagFilter", "TasteFilter", "SugarClassFilter", "TextFilter")],
    *[inh(c, "Command") for c in ("SearchCommand", "RefineCommand", "RecommendCommand")],
    agg("SearchQuery", "Filter", "0..*"), use("QueryParser", "SearchQuery", "создаёт"), use("SearchEngine", "SearchQuery"),
    agg("SearchEngine", "UtilityFunction"), agg("SearchEngine", "RelaxationAdvisor"), use("Command", "SearchEngine"),
    use("Command", "QueryParser"), use("RecommendCommand", "RecommendationService"), agg("Session", "History"),
    agg("History", "Step", "0..*"), agg("UnifiedService", "Command", "реестр"), use("Command", "Session"),
]

if __name__ == "__main__":
    for name, items in {"similarity": SIMILARITY, "rankers": RANKERS, "core": CORE, "search": SEARCH}.items():
        write(name, items)

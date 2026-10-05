# Литература и источники по мерам близости и расстояния

## Основные источники из задания

- **Большакова Е.И., Клышинский Э.С., Ландэ Д.В., Носков А.А., Пескова О.В.,
  Ягунова Е.В.** Автоматическая обработка текстов на естественном языке и
  компьютерная лингвистика. М.: МИЭМ, 2011. — 272 с. (разд. 2.7.2 «Меры
  близости и расстояния»).
  - PDF: <http://elib.nsu.ru/dsweb/Get/Resource-1583/page001.pdf>
  - Страница курса с библиографией: <https://openedu.ru/course/nsu/COMP_LING/>

- **Волкова Л.Л., Строганов Ю.В.** Об ассоциативных бинарных мерах близости
  документов: классификация и приложение к кластеризации // Новые
  информационные технологии в автоматизированных системах. 2014. № 17.
  С. 421–432.
  - <https://exa.ai/library/publication/520m2trg8p0>

## Числовые меры расстояния (ЛР 2.1a)

- Расстояние Минковского (общее семейство Lp): <https://en.wikipedia.org/wiki/Minkowski_distance>
- Евклидово расстояние (p=2): <https://en.wikipedia.org/wiki/Euclidean_distance>
- Манхэттенское расстояние (p=1): <https://en.wikipedia.org/wiki/Taxicab_geometry>
- Расстояние Чебышёва (p→∞): <https://en.wikipedia.org/wiki/Chebyshev_distance>
- Косинусная близость/расстояние: <https://en.wikipedia.org/wiki/Cosine_similarity>

## Ассоциативные бинарные меры (ЛР 2.1b)

- Индекс Жаккара: <https://en.wikipedia.org/wiki/Jaccard_index>
- Коэффициент Сёренсена–Дайса: <https://en.wikipedia.org/wiki/S%C3%B8rensen%E2%80%93Dice_coefficient>
- Коэффициент простых совпадений (Сокал–Миченер, SMC):
  <https://en.wikipedia.org/wiki/Simple_matching_coefficient>
- Роджерс–Танимото — вариант с двойным штрафом за рассогласование,
  описан в разделе «Other forms» страницы Жаккара
  (оригинал: Rogers D.J., Tanimoto T.T. A Computer Program for
  Classifying Plants // Science, 1960, 132(3434), с. 1115–1118).
- Обзор бинарных мер — см. также Волкова–Строганов выше и статью
  «Поль Жаккар и сходство экологических объектов»:
  <https://cyberleninka.ru/article/n/pol-zhakkar-i-shodstvo-ekologicheskih-obektov>

## Графовые меры на таксономии (ЛР 2.2)

**Реберные (edge-based):**

- **Rada R., Mili H., Bicknell E., Blettner M.** Development and
  Application of a Metric on Semantic Nets // IEEE Trans. on Systems,
  Man, and Cybernetics, 1989, 19(1), с. 17–30 — расстояние кратчайшего
  пути (edge counting).
  <https://ieeexplore.ieee.org/document/24528/>
- **Wu Z., Palmer M.** Verb Semantics and Lexical Selection //
  Proc. ACL-94, 1994, с. 133–138 — мера У–Палмера
  `2·depth(LCA)/(depth x + depth y)` (используется в работе).
  <https://aclanthology.org/P94-1019/>
- **Leacock C., Chodorow M.** Combining Local Context and WordNet
  Similarity for Word Sense Identification // в кн. WordNet: An
  Electronic Lexical Database, MIT Press, 1998, с. 265–283 —
  `−log(d_path / 2·D_max)`.
  <https://cir.nii.ac.jp/crid/1571698599961693184>

**Узловые (information content):**

- **Resnik P.** Using Information Content to Evaluate Semantic
  Similarity in a Taxonomy // Proc. IJCAI-95, 1995, с. 448–453 —
  `sim = IC(LCA)`, `IC(c) = −log p(c)`.
  <https://arxiv.org/abs/cmp-lg/9511007>
- **Jiang J.J., Conrath D.W.** Semantic Similarity Based on Corpus
  Statistics and Lexical Taxonomy // Proc. ROCLING X, 1997, с. 19–33 —
  расстояние `IC(x) + IC(y) − 2·IC(LCA)`.
  <https://aclanthology.org/O97-1002/> · <https://arxiv.org/abs/cmp-lg/9709008>
- **Lin D.** An Information-Theoretic Definition of Similarity //
  Proc. ICML-98, 1998, с. 296–304 — `2·IC(LCA)/(IC(x) + IC(y))`.
  <https://mlanthology.org/icml/1998/lin1998icml-information/>
  PDF: <http://www.dit.unitn.it/~p2p/RelatedWork/Matching/an-information-theoretic-definition.pdf>

**Обзор:** Semantic similarity (WordNet, все меры с формулами):
<https://en.wikipedia.org/wiki/Semantic_similarity>

## Общее

- Distance / Similarity measures overview:
  <https://en.wikipedia.org/wiki/Similarity_measure>
- Нормировка признаков (min-max и др.):
  <https://en.wikipedia.org/wiki/Feature_scaling>
- Корреляция Спирмена (использована для сравнения ранжирований мер):
  <https://en.wikipedia.org/wiki/Spearman%27s_rank_correlation_coefficient>
- EU-нормы по сахару в ликёрах (crème ≥ 250 г/л) — Регламент (EC)
  № 110/2008, Annex II:
  <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32008R0110>

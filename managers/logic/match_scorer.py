"""MatchScorer: Weighted similarity between two items, from 0 to 1, with two penalties."""
from __future__ import annotations

from managers.base.similarity_strategy import SimilarityStrategy
from managers.logic.date_similarity import DateSimilarity
from managers.logic.text_similarity import TextSimilarity
from models.item import Item


class MatchScorer:
    """Weighted similarity between two items, from 0 to 1, with two penalties.

    Composition: owns its field weights and similarity strategies. A new kind of
    comparison is a new SimilarityStrategy, without changing this class (Open/Closed).
    """

    WEIGHTS = {
        "item_type": 0.25, "item_colour": 0.20, "item_description": 0.15, "location": 0.15,
        "item_brand": 0.10, "datetime": 0.10, "item_unique_info": 0.05,
    }
    TYPE_MISMATCH_LIMIT = 0.5      # item types less similar than this halve the score
    EARLY_FOUND_PENALTY = 0.8      # multiplier when found long before it was lost

    def __init__(self, text: TextSimilarity | None = None, dates: DateSimilarity | None = None) -> None:
        self._text = text or TextSimilarity()
        self._dates = dates or DateSimilarity()
        self._strategies: dict[str, SimilarityStrategy] = {
            name: (self._dates if name == "datetime" else self._text) for name in self.WEIGHTS
        }

    def score(self, reference: Item, candidate: Item, directional: bool = True) -> float:
        """directional=True: reference is the lost report, candidate a found item (search).
        False: two found reports (duplicate check)."""
        total = weight_used = 0.0
        for name, weight in self.WEIGHTS.items():
            similarity = self._strategies[name].compare(
                reference.field(name).text, candidate.field(name).text, directional=directional)
            if similarity is None:
                continue
            total += weight * similarity
            weight_used += weight
        if weight_used == 0:
            return 0.0
        score = total / weight_used

        type_similarity = self._text.compare(reference.item_type.text, candidate.item_type.text)
        if type_similarity is not None and type_similarity < self.TYPE_MISMATCH_LIMIT:
            score *= 0.5
        if directional and self._dates.found_too_early(reference.when.text, candidate.when.text):
            score *= self.EARLY_FOUND_PENALTY
        return round(min(max(score, 0.0), 1.0), 4)

    def dates_rule_out(self, lost: Item, found: Item) -> bool:
        """True if the dates alone make a match unlikely (found >48h early, or 8+ days later)."""
        return self._dates.compare(lost.when.text, found.when.text, directional=True) == 0.0

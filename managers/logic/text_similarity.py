"""TextSimilarity: Best of word overlap and spelling similarity, after normalising synonyms."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from managers.base.similarity_strategy import SimilarityStrategy


class TextSimilarity(SimilarityStrategy):
    """Best of word overlap and spelling similarity, after normalising synonyms."""

    SYNONYMS = {
        "gray": "grey", "colour": "color", "handphone": "phone", "mobile": "phone",
        "smartphone": "phone", "earbuds": "earphones", "earpods": "earphones",
        "headphone": "headphones", "notebook": "laptop", "purse": "wallet",
    }

    def tokens(self, text: str) -> list[str]:
        """Lower-case words with synonyms replaced, e.g. "Gray Mobile" -> ["grey", "phone"]."""
        return [self.SYNONYMS.get(word, word) for word in re.findall(r"[a-z0-9]+", text.lower())]

    def compare(self, first: str, second: str, *, directional: bool = True) -> float | None:
        first_tokens, second_tokens = self.tokens(first), self.tokens(second)
        if not first_tokens or not second_tokens:
            return None
        first_set, second_set = set(first_tokens), set(second_tokens)
        shared = len(first_set & second_set)
        jaccard = shared / len(first_set | second_set)
        overlap = shared / min(len(first_set), len(second_set))
        sequence = SequenceMatcher(None, " ".join(first_tokens), " ".join(second_tokens)).ratio()
        return max(jaccard, 0.9 * overlap, sequence)

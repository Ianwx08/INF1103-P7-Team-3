"""LogicManager and its pluggable parts, one class per file:

- TextSimilarity, DateSimilarity (SimilarityStrategy) -> used by MatchScorer
- DecisionEngine with ThresholdConfig: score -> MatchDecision
- MatchingService: matches, duplicates, expiry
- rules/: the follow-up rules (FollowUpRule); ColourChoiceCorrection (ItemCorrection)
LogicManager composes these and is given (association) the AI, data and IO managers.
"""

"""LogicManager and its pluggable parts, one class per file:

- TextSimilarity, DateSimilarity (SimilarityStrategy) -> used by MatchScorer
- DecisionEngine with ThresholdConfig: score -> MatchDecision
- MatchingService: matches, duplicates, expiry (ordinary items only)
- rules/: the follow-up rules (FollowUpRule); ColourChoiceCorrection (ItemCorrection)
- overview/: sort orders (ItemSortOrder) and OverviewService for "View stored items"
- EscalationService: emails the admins (at most once per item per day) about HIGH_VALUE  found items left unclaimed for more than 7 days
LogicManager composes these and is given (association) the AI, data and IO managers.
"""

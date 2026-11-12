"""Matching logic with hard-coded sample AI replies. Same expected values as Phase 1. No API calls."""
import unittest
from datetime import datetime

from managers.base.similarity_strategy import SimilarityStrategy
from managers.logic.date_similarity import DateSimilarity
from managers.logic.decision_engine import DecisionEngine
from managers.logic.match_scorer import MatchScorer
from managers.logic.matching_service import MatchingService
from managers.logic.text_similarity import TextSimilarity
from managers.logic.threshold_config import ThresholdConfig
from models import ExtractedField, FoundItem, Item, MatchDecision
from tests.helpers import SampleReplies

ai_reply = SampleReplies.ai_reply

class LogicSamples:
    """Builds stored found items and date variants for the matching tests."""

    @staticmethod
    def stored(reply, item_id, reported_at="2026-10-10T16:00", status="active") -> FoundItem:
        item = Item.from_ai_response("found", reply)
        return FoundItem(item.fields, item.flags, item_id, reported_at, status)

    @staticmethod
    def with_date(item, value):
        return item.with_field("datetime", ExtractedField(value, 0.95))


stored = LogicSamples.stored
with_date = LogicSamples.with_date

LOST_PHONE = Item.from_ai_response("lost", ai_reply(
    "lost", "Samsung Galaxy S25", "phone", "black", "Samsung", "cracked screen protector",
    "2026-10-10T14:00", "SIT Punggol food court"))


FOUND_PHONE = stored(ai_reply("found", "Samsung Galaxy S25", "phone", "black", "Samsung",
                              "cracked screen protector", "2026-10-10T15:00", "SIT Punggol food court"), "FND-0001")
FOUND_WHITE_PHONE = stored(ai_reply("found", "Samsung phone", "phone", "white", None, None,
                                    "2026-10-10T15:00", "Tampines Mall"), "FND-0002")
FOUND_UMBRELLA = stored(ai_reply("found", "red foldable umbrella", "umbrella", "red", None, None,
                                 "2026-10-10T15:00", "Jurong East MRT station"), "FND-0003")


class TestTextSimilarity(unittest.TestCase):
    def setUp(self):
        self.text = TextSimilarity()

    def test_is_a_similarity_strategy(self):
        self.assertIsInstance(self.text, SimilarityStrategy)

    def test_tokens_and_synonyms(self):
        self.assertEqual(self.text.tokens("Gray Mobile!"), ["grey", "phone"])
        self.assertEqual(self.text.compare("Gray", "grey"), 1.0)

    def test_scores(self):
        self.assertGreater(self.text.compare("Hydro Flask", "Hydroflask"), 0.9)
        self.assertAlmostEqual(self.text.compare("SIT Punggol food court", "Punggol campus food court"), 0.77, places=2)
        self.assertLess(self.text.compare("wallet", "umbrella"), 0.5)
        self.assertIsNone(self.text.compare("black", ""))


class TestDateSimilarity(unittest.TestCase):
    def setUp(self):
        self.dates = DateSimilarity()
        self.lost = "2026-10-10T15:00"

    def test_parse(self):
        self.assertEqual(DateSimilarity.parse("2026-10-10T15:00"), datetime(2026, 10, 10, 15, 0))
        self.assertIsNone(DateSimilarity.parse("10 Oct 3pm"))

    def test_48_hour_tolerance(self):
        self.assertFalse(self.dates.found_too_early(self.lost, "2026-10-09T15:00"))
        self.assertTrue(self.dates.found_too_early(self.lost, "2026-10-08T14:00"))

    def test_scores_over_time(self):
        self.assertEqual(self.dates.compare(self.lost, "2026-10-10T18:00"), 1.0)
        self.assertAlmostEqual(self.dates.compare(self.lost, "2026-10-12T15:00"), 0.857, places=3)
        self.assertEqual(self.dates.compare(self.lost, "2026-10-18T15:00"), 0.0)

    def test_direction(self):
        self.assertEqual(self.dates.compare(self.lost, "2026-10-05T15:00", directional=True), 0.0)
        self.assertGreater(self.dates.compare(self.lost, "2026-10-05T15:00", directional=False), 0.0)
        self.assertIsNone(self.dates.compare(self.lost, ""))


class TestMatchScorer(unittest.TestCase):
    def setUp(self):
        self.scorer = MatchScorer()

    def test_same_phone(self):
        self.assertEqual(self.scorer.score(LOST_PHONE, FOUND_PHONE), 1.0)

    def test_similar_phone_elsewhere(self):
        self.assertAlmostEqual(self.scorer.score(LOST_PHONE, FOUND_WHITE_PHONE), 0.53, places=2)

    def test_unrelated_item_gets_type_penalty(self):
        self.assertLess(self.scorer.score(LOST_PHONE, FOUND_UMBRELLA), 0.5)
        wallet = FOUND_PHONE.with_field("item_type", ExtractedField("wallet", 0.95)) \
                            .with_field("item_description", ExtractedField("black leather wallet", 0.95))
        self.assertLess(self.scorer.score(LOST_PHONE, wallet), 0.5)

    def test_found_long_before_lost_is_penalised_exactly(self):
        early = with_date(FOUND_PHONE, "2026-10-05T15:00")
        self.assertAlmostEqual(self.scorer.score(LOST_PHONE, early), round(0.9 * 0.8, 4))

    def test_missing_brand_not_counted_as_mismatch(self):
        no_brand = FOUND_PHONE.with_field("item_brand", ExtractedField(None, 0.0))
        self.assertGreaterEqual(self.scorer.score(LOST_PHONE, no_brand), 0.95)

    def test_dates_rule_out(self):
        lost = with_date(LOST_PHONE, "2026-10-09T02:00")
        self.assertTrue(self.scorer.dates_rule_out(lost, with_date(FOUND_PHONE, "2026-10-21T02:00")))
        self.assertTrue(self.scorer.dates_rule_out(lost, with_date(FOUND_PHONE, "2026-10-06T02:00")))
        self.assertFalse(self.scorer.dates_rule_out(lost, with_date(FOUND_PHONE, "2026-10-10T02:00")))
        self.assertFalse(self.scorer.dates_rule_out(lost, with_date(FOUND_PHONE, "")))


class TestDecisionEngine(unittest.TestCase):
    def test_default_thresholds(self):
        engine = DecisionEngine()
        self.assertIs(engine.decide(0.85), MatchDecision.DISPLAY)
        self.assertIs(engine.decide(0.60), MatchDecision.REVIEW)
        self.assertIs(engine.decide(0.20), MatchDecision.HIDE)

    def test_configurable_thresholds(self):
        self.assertIs(DecisionEngine(MatchingService.MATCH_CONFIG).decide(0.72), MatchDecision.DISPLAY)

    def test_invalid_scores_and_config(self):
        engine = DecisionEngine()
        with self.assertRaises(TypeError):
            engine.decide(True)
        with self.assertRaises(ValueError):
            engine.decide(1.5)
        with self.assertRaises(ValueError):
            ThresholdConfig(display_threshold=0.4, review_threshold=0.6)
        with self.assertRaises(ValueError):
            ThresholdConfig(max_results=0)

    def test_sorting_and_caps(self):
        engine = DecisionEngine()
        items = [stored(ai_reply(), f"FND-{n:04d}") for n in range(8)]
        scored = [(items[0], 0.4), (items[1], 0.9), (items[2], 0.6)]
        self.assertEqual([m.score for m in engine.evaluate(scored)], [0.9, 0.6, 0.4])
        self.assertEqual(len(engine.displayable([(i, 0.95) for i in items])), 5)
        self.assertEqual([m.item.item_id for m in engine.review(scored)], ["FND-0002"])


class TestMatchingService(unittest.TestCase):
    def setUp(self):
        self.matching = MatchingService()

    def test_find_matches_splits_top_and_possible(self):
        top, possible = self.matching.find_matches(LOST_PHONE, [FOUND_PHONE, FOUND_WHITE_PHONE, FOUND_UMBRELLA])
        self.assertEqual([m.item.item_id for m in top], ["FND-0001"])
        self.assertEqual([m.item.item_id for m in possible], ["FND-0002"])
        self.assertIs(top[0].item, FOUND_PHONE)

    def test_nothing_stored(self):
        self.assertEqual(self.matching.find_matches(LOST_PHONE, []), ([], []))

    def test_dates_that_rule_out_a_match_cap_it_to_possible(self):
        lost = with_date(LOST_PHONE, "2026-10-09T02:00")
        for found_date in ("2026-10-21T02:00", "2026-10-06T02:00"):
            top, possible = self.matching.find_matches(lost, [with_date(FOUND_PHONE, found_date)])
            self.assertEqual((len(top), len(possible)), (0, 1), found_date)
        top, _ = self.matching.find_matches(lost, [with_date(FOUND_PHONE, "2026-10-10T02:00")])
        self.assertEqual(len(top), 1)
        weak = with_date(FOUND_UMBRELLA, "2026-10-21T02:00")
        self.assertEqual(self.matching.find_matches(lost, [weak]), ([], []))

    def test_unsaved_items_are_skipped(self):
        unsaved = Item.from_ai_response("found", ai_reply())
        self.assertEqual(self.matching.find_matches(LOST_PHONE, [unsaved]), ([], []))

    def test_duplicates(self):
        new = Item.from_ai_response("found", ai_reply("found", "Samsung Galaxy S25", "phone", "black", "Samsung",
                                                      "cracked screen protector", "2026-10-10T15:00",
                                                      "SIT Punggol food court"))
        found = self.matching.find_duplicates(new, [FOUND_PHONE, FOUND_WHITE_PHONE, FOUND_UMBRELLA])
        self.assertEqual([i.item_id for i in found], ["FND-0001"])

    def test_expired(self):
        now = datetime(2026, 10, 18, 12, 0)
        items = [stored(ai_reply(), "OLD", "2026-10-10T12:00"), stored(ai_reply(), "EXACT", "2026-10-11T12:00"),
                 stored(ai_reply(), "NEW", "2026-10-17T12:00"), stored(ai_reply(), "DONE", "2026-09-01T12:00", "archived"),
                 stored(ai_reply(), "BROKEN", "not a date")]
        self.assertEqual([i.item_id for i in self.matching.expired(items, now=now)], ["OLD"])


if __name__ == "__main__":
    unittest.main()

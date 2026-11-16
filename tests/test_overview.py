"""New feature: overview of stored items, sorted by date or item type. No API calls."""
import unittest
from managers.base.item_sort_order import ItemSortOrder
from managers.logic.overview.found_date_order import FoundDateOrder
from managers.logic.overview.item_type_order import ItemTypeOrder
from managers.logic.overview.overview_service import OverviewService
from models import FoundItem, Item, StoredItemsOverview
from tests.helpers import SampleReplies


ai_reply = SampleReplies.ai_reply


class OverviewSamples:
    """Stored found items with chosen types, dates and status."""

    @staticmethod
    def item(item_id, item_type, when, status="active", unique=None, description=None) -> FoundItem:
        base = Item.from_ai_response("found", ai_reply(item_type=item_type, when=when, unique=unique,
                                                       description=description or f"{item_type} {item_id}"))
        return FoundItem(base.fields, base.flags, item_id, "2026-10-14T12:00", status)

    @staticmethod
    def ids(items) -> list[str]:
        """The item IDs, in order."""
        return [item.item_id for item in items]


sample = OverviewSamples.item
ids = OverviewSamples.ids
PHONE_OLD = sample("FND-0001", "phone", "2026-10-08T09:00")
WALLET = sample("FND-0002", "wallet", "2026-10-12T15:00")
PHONE_NEW = sample("FND-0003", "Phone", "2026-10-13T18:00")
NO_DATE = sample("FND-0004", "umbrella", None)
NO_TYPE = sample("FND-0005", None, "2026-10-11T10:00")
ARCHIVED = sample("FND-0006", "phone", "2026-10-01T10:00", status="archived")
ITEMS = [PHONE_OLD, WALLET, PHONE_NEW, NO_DATE, NO_TYPE]
ALL_ORDERS = [FoundDateOrder(), FoundDateOrder(newest_first=False), ItemTypeOrder()]


class TestSortOrders(unittest.TestCase):
    def test_orders_are_item_sort_orders(self):
        for order in ALL_ORDERS:
            self.assertIsInstance(order, ItemSortOrder)

    def test_newest_first_with_undated_last(self):
        self.assertEqual(ids(FoundDateOrder().sort(ITEMS)),
                         ["FND-0003", "FND-0002", "FND-0005", "FND-0001", "FND-0004"])

    def test_oldest_first_with_undated_still_last(self):
        self.assertEqual(ids(FoundDateOrder(newest_first=False).sort(ITEMS)),
                         ["FND-0001", "FND-0005", "FND-0002", "FND-0003", "FND-0004"])

    def test_item_type_a_to_z_ignoring_case_newest_first_within_type(self):
        self.assertEqual(ids(ItemTypeOrder().sort(ITEMS)),
                         ["FND-0003", "FND-0001", "FND-0004", "FND-0002", "FND-0005"])

    def test_item_type_with_a_different_tie_break(self):
        order = ItemTypeOrder(within_type=FoundDateOrder(newest_first=False))
        self.assertEqual(ids(order.sort([PHONE_NEW, PHONE_OLD])), ["FND-0001", "FND-0003"])

    def test_sorting_returns_a_new_list_with_the_same_items(self):
        original = list(ITEMS)
        for order in ALL_ORDERS:
            result = order.sort(ITEMS)
            self.assertEqual(sorted(ids(result)), sorted(ids(ITEMS)), order.label)
            self.assertIsNot(result, ITEMS)
        self.assertEqual(ITEMS, original)
        self.assertEqual(FoundDateOrder().sort([]), [])


class TestOverviewService(unittest.TestCase):
    def setUp(self):
        self.service = OverviewService()

    def test_menu_labels(self):
        self.assertEqual(self.service.labels,
                         ["Date found (newest first)", "Date found (oldest first)", "Item type (A-Z)"])

    def test_build_lists_active_items_and_counts_types(self):
        overview = self.service.build(ITEMS + [ARCHIVED], self.service.find_order("Item type (A-Z)"))
        self.assertIsInstance(overview, StoredItemsOverview)
        self.assertEqual(overview.total, 5)
        self.assertNotIn("FND-0006", ids(overview.items))
        self.assertEqual(overview.archived_count, 1)
        self.assertEqual(overview.type_counts,
                         (("phone", 2), ("umbrella", 1), ("unknown", 1), ("wallet", 1)))
        self.assertEqual(overview.sort_label, "Item type (A-Z)")

    def test_empty_overview(self):
        overview = self.service.build([ARCHIVED], self.service.orders[0])
        self.assertTrue(overview.is_empty())
        self.assertEqual((overview.archived_count, overview.type_counts), (1, ()))

    def test_unknown_label_and_bad_configuration(self):
        with self.assertRaises(KeyError):
            self.service.find_order("Colour")
        with self.assertRaises(ValueError):
            OverviewService([])
        with self.assertRaises(ValueError):
            OverviewService([FoundDateOrder(), FoundDateOrder()])

    def test_a_new_sort_order_needs_no_change_to_the_service(self):
        class ByIdDescending(ItemSortOrder):
            label = "Reference number (highest first)"

            def sort(self, items):
                return sorted(items, key=lambda item: item.item_id, reverse=True)

        service = OverviewService([ByIdDescending()])
        overview = service.build(ITEMS, service.find_order("Reference number (highest first)"))
        self.assertEqual(ids(overview.items)[0], "FND-0005")

    def test_overview_is_read_only(self):
        overview = self.service.build(ITEMS, self.service.orders[0])
        with self.assertRaises(AttributeError):
            overview.sort_label = "changed"
        with self.assertRaises(ValueError):
            StoredItemsOverview("x", (), archived_count=-1)


if __name__ == "__main__":
    unittest.main()
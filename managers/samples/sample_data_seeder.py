"""SampleDataSeeder: Adds the samples to any BaseDataManager, skipping ones that are already active there."""
from __future__ import annotations

from managers.base.base_data_manager import BaseDataManager
from managers.samples.sample_data_loader import SampleDataLoader
from models.item import Item


class SampleDataSeeder:
    """Adds the samples to any BaseDataManager, skipping ones that are already active there.

    Running it twice does not create copies. Once the samples have been archived (7 days
    after loading), running it again adds fresh ones.
    """

    def __init__(self, loader: SampleDataLoader, data: BaseDataManager) -> None:
        self._loader = loader
        self._data = data

    @staticmethod
    def key(item: Item) -> tuple[str, str]:
        """What makes a sample "the same": its description and place, ignoring case."""
        return item.description.text.lower(), item.location.text.lower()

    def seed(self) -> tuple[int, int]:
        """Store the samples; returns (added, skipped as already present)."""
        present = {self.key(item) for item in self._data.get_active()}
        added = skipped = 0
        for item in self._loader.load():
            if self.key(item) in present:
                skipped += 1
                continue
            self._data.add(item)
            present.add(self.key(item))
            added += 1
        return added, skipped

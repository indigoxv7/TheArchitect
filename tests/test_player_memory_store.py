import tempfile
import unittest
from pathlib import Path

from src.domain.main_character_memory import EventRecord, utc_now_iso
from src.persistence.player_memory import PlayerMemoryStore


class TestPlayerMemoryStore(unittest.TestCase):
    def test_initialize_creates_database_and_round_trips_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'PlayerMemory' / 'player_memory.sqlite'
            store = PlayerMemoryStore(str(db_path))
            store.initialize()

            self.assertTrue(db_path.exists())

            event = store.insert_event(
                EventRecord(
                    player_id=77,
                    event_id=0,
                    created_at=utc_now_iso(),
                    event_type='test_event',
                    summary='A player-scoped event',
                    participants=['Hero0'],
                    tags=['test'],
                    location='Arena',
                    importance=0.5,
                )
            )

            loaded = store.list_events_for_character(77, 'Hero0', limit=10)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].event_id, event.event_id)
            self.assertEqual(loaded[0].summary, 'A player-scoped event')
            self.assertEqual(loaded[0].tags, ['test'])


if __name__ == '__main__':
    unittest.main()


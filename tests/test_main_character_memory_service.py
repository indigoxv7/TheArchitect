import tempfile
import unittest
from pathlib import Path

from src.domain.MainCharacter import MainCharacter
from src.domain.main_character_memory import CharacterMemory, Relationship, SemanticFact, utc_now_iso
from src.domain.player_functions import Player
from src.persistence.player_memory_store import PlayerMemoryStore
from src.services.main_character_memory_service import MainCharacterMemoryService
from src.services.openai_narrative_service import MemoryDistillationModel, ReflectionModel, RelationshipDeltaModel, TurnResponseModel


class StubPlayerService:
    def __init__(self, players):
        self.players = players

    def get_player_sync(self, player_id: int):
        return self.players.get(int(player_id))


class FakeOpenAIService:
    def __init__(self):
        self.turn_model = 'fake-turn-model'
        self.memory_model = 'fake-memory-model'
        self.embedding_model = 'fake-embedding-model'

    def is_configured(self) -> bool:
        return True

    def embed_text(self, text: str) -> list[float]:
        normalized = str(text or '').lower()
        return [
            1.0 if 'forest' in normalized else 0.0,
            1.0 if 'castle' in normalized else 0.0,
            1.0 if 'promise' in normalized else 0.0,
            1.0 if 'companion' in normalized else 0.0,
            float(len(normalized) % 7) / 10.0,
        ]

    def generate_turn(self, prompt_packet):
        return TurnResponseModel(
            spoken_text='I will keep my promise.',
            action_summary='promised to protect the companion in the forest',
            scene_tags=['promise', 'forest'],
            self_emotion='determined',
            relationship_deltas=[
                RelationshipDeltaModel(
                    target_character_instance_id='Companion0',
                    affinity_delta=0.6,
                    trust_delta=0.9,
                    fear_delta=-0.1,
                    respect_delta=0.4,
                    reason='Protective promise',
                )
            ],
        )

    def distill_memory(self, character_packet, event_packet):
        character_id = character_packet.get('playerInstanceId', '')
        target_id = 'Companion0' if character_id == 'Hero0' else 'Hero0'
        return MemoryDistillationModel(
            summary=f"{character_packet.get('name', 'Unknown')} remembers a promise in the forest.",
            importance=0.9,
            tags=['forest', 'promise'],
            fact_candidates=['Keeps promises under pressure'],
            relationship_deltas=[
                RelationshipDeltaModel(
                    target_character_instance_id=target_id,
                    affinity_delta=0.4,
                    trust_delta=0.7,
                    fear_delta=-0.1,
                    respect_delta=0.2,
                    reason='Shared promise',
                )
            ],
        )

    def reflect(self, character_packet, memories):
        return ReflectionModel(
            insights=['Values loyalty in dangerous situations'],
            facts=['Believes promises matter'],
            tags=['promise', 'loyalty'],
        )


class TestMainCharacterMemoryService(unittest.TestCase):
    def _build_service(self, temp_dir: str):
        hero = MainCharacter(name='Hero', playerInstanceId='Hero0')
        hero.description = 'A determined adventurer.'
        hero.characterInfo.goal = 'Protect allies'
        companion = MainCharacter(name='Companion', playerInstanceId='Companion0')
        companion.characterInfo.goal = 'Support the hero'
        player_one = Player(1, characters=[hero, companion])

        rival = MainCharacter(name='Rival', playerInstanceId='Hero0')
        rival.characterInfo.goal = 'Win at any cost'
        player_two = Player(2, characters=[rival])

        store = PlayerMemoryStore(str(Path(temp_dir) / 'player_memory.sqlite'))
        service = MainCharacterMemoryService(
            memory_store=store,
            player_service=StubPlayerService({1: player_one, 2: player_two}),
            openai_service=FakeOpenAIService(),
        )
        service.initialize()
        return service, store

    def test_player_scope_isolation_keeps_histories_separate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, store = self._build_service(temp_dir)
            store.insert_memory(
                CharacterMemory(
                    player_id=1,
                    memory_id=0,
                    character_instance_id='Hero0',
                    created_at=utc_now_iso(),
                    summary='Player one memory',
                    importance=0.7,
                    tags=['forest'],
                    embedding=service.openai_service.embed_text('forest'),
                )
            )
            store.insert_fact(
                SemanticFact(
                    player_id=1,
                    fact_id=0,
                    character_instance_id='Hero0',
                    created_at=utc_now_iso(),
                    fact_text='Player one fact',
                    confidence=0.8,
                    tags=['forest'],
                    embedding=service.openai_service.embed_text('forest'),
                )
            )
            store.upsert_relationship(
                Relationship(
                    player_id=1,
                    character_instance_id='Hero0',
                    target_character_instance_id='Companion0',
                    trust=0.5,
                )
            )
            store.insert_memory(
                CharacterMemory(
                    player_id=2,
                    memory_id=0,
                    character_instance_id='Hero0',
                    created_at=utc_now_iso(),
                    summary='Player two memory',
                    importance=0.5,
                    tags=['castle'],
                    embedding=service.openai_service.embed_text('castle'),
                )
            )

            snapshot_one = service.build_character_snapshot(1, 'Hero0')
            snapshot_two = service.build_character_snapshot(2, 'Hero0')

            self.assertEqual(snapshot_one['memories'][0]['summary'], 'Player one memory')
            self.assertEqual(snapshot_one['facts'][0]['fact_text'], 'Player one fact')
            self.assertEqual(snapshot_one['relationships'][0]['target_character_instance_id'], 'Companion0')
            self.assertEqual(snapshot_two['memories'][0]['summary'], 'Player two memory')
            self.assertEqual(snapshot_two['facts'], [])
            self.assertEqual(snapshot_two['relationships'], [])

    def test_build_prompt_packet_prefers_matching_recalled_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, store = self._build_service(temp_dir)
            store.insert_memory(
                CharacterMemory(
                    player_id=1,
                    memory_id=0,
                    character_instance_id='Hero0',
                    created_at=utc_now_iso(),
                    summary='A promise made in the forest.',
                    importance=0.9,
                    tags=['forest', 'promise'],
                    embedding=service.openai_service.embed_text('forest promise'),
                )
            )
            store.insert_memory(
                CharacterMemory(
                    player_id=1,
                    memory_id=0,
                    character_instance_id='Hero0',
                    created_at=utc_now_iso(),
                    summary='A quiet negotiation in the castle.',
                    importance=0.4,
                    tags=['castle'],
                    embedding=service.openai_service.embed_text('castle negotiation'),
                )
            )

            packet = service.build_prompt_packet(
                1,
                'Hero0',
                {
                    'location': 'Forest Camp',
                    'stakes': 'Keep the promise',
                    'sensory_details': 'Rain and pine smoke',
                    'latest_utterance': 'You said you would stay.',
                    'prompt': 'Respond to the companion.',
                    'participant_ids': ['Companion0'],
                },
            )

            self.assertGreaterEqual(len(packet['recalled_memories']), 1)
            self.assertEqual(packet['recalled_memories'][0]['summary'], 'A promise made in the forest.')

    def test_generate_turn_persists_events_memories_facts_and_relationships(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _store = self._build_service(temp_dir)

            result = service.generate_turn(
                1,
                'Hero0',
                {
                    'location': 'Forest Camp',
                    'stakes': 'A dangerous promise',
                    'sensory_details': 'Cold rain and torchlight',
                    'latest_utterance': 'Will you really stay?',
                    'prompt': 'Answer your companion.',
                    'participant_ids': ['Companion0'],
                },
            )

            self.assertGreater(result['event_id'], 0)
            self.assertGreater(result['turn_id'], 0)
            self.assertGreaterEqual(len(result['memory_ids']), 2)
            self.assertGreaterEqual(result['facts_added'], 2)
            self.assertGreaterEqual(result['relationships_updated'], 2)

            snapshot = service.build_character_snapshot(1, 'Hero0')
            self.assertEqual(len(snapshot['events']), 1)
            self.assertGreaterEqual(len(snapshot['memories']), 1)
            self.assertGreaterEqual(len(snapshot['facts']), 1)
            self.assertGreaterEqual(len(snapshot['relationships']), 1)
            self.assertIn('promise', snapshot['memories'][0]['summary'].lower())


if __name__ == '__main__':
    unittest.main()

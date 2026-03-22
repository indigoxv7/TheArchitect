import asyncio
import unittest
from types import SimpleNamespace

from src.services.battle_runtime_service import BattleRuntimeService


class _FakeResponse:
    def __init__(self):
        self._done = False
        self.deferred = False
        self.sent_messages = []

    def is_done(self):
        return self._done

    async def defer(self):
        self.deferred = True
        self._done = True

    async def send_message(self, content=None, **kwargs):
        self.sent_messages.append((content, kwargs))
        self._done = True


class _FakeMessage:
    def __init__(self):
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


class _FakeFollowup:
    def __init__(self):
        self.messages = []

    async def send(self, content=None, **kwargs):
        self.messages.append((content, kwargs))


class _FakeBattleService:
    def __init__(self, battle):
        self._battle = battle
        self.resolved = False

    def get_active_battle(self, _player_id):
        return self._battle

    def resolve_exchange(self, battle, persist=True, record_memory=True):
        self.resolved = True
        self.persist = persist
        self.record_memory = record_memory
        return SimpleNamespace(exchange_number=4)


class TestBattleRuntimeService(unittest.TestCase):
    def test_advance_exchange_defers_before_render(self):
        battle = SimpleNamespace(player_id=123)
        runtime = BattleRuntimeService(_FakeBattleService(battle))

        called = {}

        async def fake_render(interaction, rendered_battle, message=None, note=None):
            called['response_done_during_render'] = interaction.response.is_done()
            called['battle'] = rendered_battle
            called['note'] = note

        runtime.render_battle = fake_render
        interaction = SimpleNamespace(
            user=SimpleNamespace(id=123),
            response=_FakeResponse(),
            message=_FakeMessage(),
            followup=_FakeFollowup(),
        )

        asyncio.run(runtime.advance_exchange(interaction, 123))

        self.assertTrue(interaction.response.deferred)
        self.assertTrue(called['response_done_during_render'])
        self.assertIs(called['battle'], battle)
        self.assertIsNone(called['note'])


if __name__ == '__main__':
    unittest.main()

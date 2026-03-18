import unittest

from src.domain.combat_timing import (
    CombatRuntimeState,
    ExertionLevel,
    action_interval_seconds,
    initialize_runtime_fields,
    schedule_next_action,
    spend_stamina,
    sync_stamina,
)


class TestCombatTiming(unittest.TestCase):
    def test_stamina_regen_updates_exertion_state(self):
        runtime = CombatRuntimeState(stamina_current=75.0, stamina_limit=75.0, stamina_regen_per_second=2.5)
        initialize_runtime_fields(
            runtime,
            stamina_limit=75.0,
            stamina_regen_per_second=2.5,
            stamina_current=75.0,
        )

        spend_stamina(runtime, 80.0, 0.0)
        self.assertEqual(runtime.exertion_level, ExertionLevel.TIRED.name)

        sync_stamina(runtime, 2.0)
        self.assertEqual(runtime.stamina_current, 0.0)
        self.assertEqual(runtime.exertion_level, ExertionLevel.FRESH.name)

    def test_next_action_interval_scales_with_speed_and_exhaustion(self):
        runtime = CombatRuntimeState(stamina_current=75.0, stamina_limit=75.0, stamina_regen_per_second=2.5)
        initialize_runtime_fields(
            runtime,
            stamina_limit=75.0,
            stamina_regen_per_second=2.5,
            stamina_current=75.0,
        )

        next_time = schedule_next_action(runtime, base_speed=2.0, turn_start_time=0.0)
        self.assertAlmostEqual(next_time, 3.0)
        self.assertAlmostEqual(action_interval_seconds(2.0, runtime.exertion_level), 3.0)

        spend_stamina(runtime, 160.0, 0.0)
        exhausted_next = schedule_next_action(runtime, base_speed=2.0, turn_start_time=0.0)
        self.assertEqual(runtime.exertion_level, ExertionLevel.EXHAUSTED.name)
        self.assertAlmostEqual(exhausted_next, 6.0)


if __name__ == "__main__":
    unittest.main()

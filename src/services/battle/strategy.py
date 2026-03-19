from __future__ import annotations

import re
from typing import Any

from src.config.tuning import battle_factor, battle_factor_int
from src.domain.combat.state import BattleState


class BattleStrategyMixin:
    def _is_adversarial_strategy(self, text: str) -> bool:
        lowered = str(text or "").strip().lower()
        if not lowered:
            return True
        return any(re.search(pattern, lowered) for pattern in self.STRATEGY_INJECTION_PATTERNS)

    def _neutral_strategy_result(self, reason: str) -> dict[str, Any]:
        return {
            "score": 5,
            "reasons": [reason],
            "risk_flags": [],
            "confidence": 0.0,
        }

    def judge_strategy(self, battle: BattleState, strategy_text: str) -> dict[str, Any]:
        text = str(strategy_text or "").strip()
        if self._is_adversarial_strategy(text):
            return self._neutral_strategy_result(
                "Strategy text was empty or looked adversarial, so neutral orders were applied."
            )
        if self.openai_service is None or not getattr(self.openai_service, "is_configured", lambda: False)():
            return self._neutral_strategy_result("OpenAI is not configured, so neutral orders were applied.")
        if not hasattr(self.openai_service, "judge_combat_strategy"):
            return self._neutral_strategy_result("Combat judge is unavailable, so neutral orders were applied.")

        prompt_packet = {
            "encounter": battle.encounter.to_dict(),
            "orders": battle.orders.to_dict(),
            "strategy_text": text,
            "recent_highlights": [summary.to_dict() for summary in battle.recent_summaries[-2:]],
        }
        results = []
        for _ in range(3):
            try:
                judgment = self.openai_service.judge_combat_strategy(prompt_packet)
                results.append(judgment)
            except Exception:
                continue
        if not results:
            return self._neutral_strategy_result("Strategy judge failed, so neutral orders were applied.")
        scores = sorted(int(max(1, min(10, getattr(result, "score", 5)))) for result in results)
        median_score = scores[len(scores) // 2]
        median_result = sorted(results, key=lambda result: int(max(1, min(10, getattr(result, "score", 5)))))[
            len(results) // 2
        ]
        return {
            "score": median_score,
            "reasons": list(getattr(median_result, "reasons", []) or []),
            "risk_flags": list(getattr(median_result, "risk_flags", []) or []),
            "confidence": float(getattr(median_result, "confidence", 0.0) or 0.0),
        }

    def apply_strategy(self, battle: BattleState, strategy_text: str) -> dict[str, Any]:
        judgment = self.judge_strategy(battle, strategy_text)
        score = int(judgment["score"])
        battle.orders.strategy_text = strategy_text
        battle.orders.strategy_score = score
        battle.orders.strategy_reasons = list(judgment["reasons"])
        battle.orders.strategy_risk_flags = list(judgment["risk_flags"])
        battle.orders.strategy_confidence = float(judgment["confidence"])
        if score <= battle_factor_int("strategy_low_score_max", 3):
            battle.orders.lane_discipline_modifier = battle_factor("strategy_low_lane_discipline_modifier", -0.05)
            battle.orders.resource_efficiency_modifier = battle_factor(
                "strategy_low_resource_efficiency_modifier", -0.10
            )
            battle.orders.width_control_bonus = 0
        elif score <= battle_factor_int("strategy_mid_score_max", 6):
            battle.orders.lane_discipline_modifier = battle_factor("strategy_mid_lane_discipline_modifier", 0.0)
            battle.orders.resource_efficiency_modifier = battle_factor("strategy_mid_resource_efficiency_modifier", 0.0)
            battle.orders.width_control_bonus = 0
        elif score <= battle_factor_int("strategy_high_score_max", 8):
            battle.orders.lane_discipline_modifier = battle_factor("strategy_high_lane_discipline_modifier", 0.05)
            battle.orders.resource_efficiency_modifier = battle_factor(
                "strategy_high_resource_efficiency_modifier", 0.05
            )
            battle.orders.width_control_bonus = 0
        else:
            battle.orders.lane_discipline_modifier = battle_factor("strategy_top_lane_discipline_modifier", 0.10)
            battle.orders.resource_efficiency_modifier = battle_factor(
                "strategy_top_resource_efficiency_modifier", 0.10
            )
            battle.orders.width_control_bonus = battle_factor_int("strategy_top_width_control_bonus", 1)
        battle.cached_victory_odds = None
        battle.cached_orders_signature = ""
        self.save_battle(battle)
        return judgment

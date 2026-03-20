from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any

from src.domain.mission.values import clamp_fraction, clamp_non_negative_int


@dataclass
class MissionMapGenerationRange:
    totalNodesLow: int = 60
    totalNodesHigh: int = 60
    narrownessLow: float = 0.5
    narrownessHigh: float = 0.5
    connectednessLow: float = 0.25
    connectednessHigh: float = 0.25
    deadEndLikelihoodLow: float = 0.7
    deadEndLikelihoodHigh: float = 0.7
    nodeJitterFractionLow: float = 0.45
    nodeJitterFractionHigh: float = 0.45

    def __post_init__(self):
        self.totalNodesLow = clamp_non_negative_int(self.totalNodesLow, 60) or 1
        self.totalNodesHigh = clamp_non_negative_int(self.totalNodesHigh, self.totalNodesLow) or self.totalNodesLow
        if self.totalNodesHigh < self.totalNodesLow:
            self.totalNodesHigh = self.totalNodesLow

        self.narrownessLow = clamp_fraction(self.narrownessLow, 0.5)
        self.narrownessHigh = clamp_fraction(self.narrownessHigh, self.narrownessLow)
        if self.narrownessHigh < self.narrownessLow:
            self.narrownessHigh = self.narrownessLow

        self.connectednessLow = clamp_fraction(self.connectednessLow, 0.25)
        self.connectednessHigh = clamp_fraction(self.connectednessHigh, self.connectednessLow)
        if self.connectednessHigh < self.connectednessLow:
            self.connectednessHigh = self.connectednessLow

        self.deadEndLikelihoodLow = clamp_fraction(self.deadEndLikelihoodLow, 0.7)
        self.deadEndLikelihoodHigh = clamp_fraction(self.deadEndLikelihoodHigh, self.deadEndLikelihoodLow)
        if self.deadEndLikelihoodHigh < self.deadEndLikelihoodLow:
            self.deadEndLikelihoodHigh = self.deadEndLikelihoodLow

        self.nodeJitterFractionLow = clamp_fraction(self.nodeJitterFractionLow, 0.45)
        self.nodeJitterFractionHigh = clamp_fraction(self.nodeJitterFractionHigh, self.nodeJitterFractionLow)
        if self.nodeJitterFractionHigh < self.nodeJitterFractionLow:
            self.nodeJitterFractionHigh = self.nodeJitterFractionLow

    def to_dict(self) -> dict[str, Any]:
        return {
            "totalNodesLow": self.totalNodesLow,
            "totalNodesHigh": self.totalNodesHigh,
            "narrownessLow": self.narrownessLow,
            "narrownessHigh": self.narrownessHigh,
            "connectednessLow": self.connectednessLow,
            "connectednessHigh": self.connectednessHigh,
            "deadEndLikelihoodLow": self.deadEndLikelihoodLow,
            "deadEndLikelihoodHigh": self.deadEndLikelihoodHigh,
            "nodeJitterFractionLow": self.nodeJitterFractionLow,
            "nodeJitterFractionHigh": self.nodeJitterFractionHigh,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MissionMapGenerationRange":
        if not isinstance(data, dict):
            return cls()
        return cls(
            totalNodesLow=data.get("totalNodesLow", 60),
            totalNodesHigh=data.get("totalNodesHigh", data.get("totalNodesLow", 60)),
            narrownessLow=data.get("narrownessLow", 0.5),
            narrownessHigh=data.get("narrownessHigh", data.get("narrownessLow", 0.5)),
            connectednessLow=data.get("connectednessLow", 0.25),
            connectednessHigh=data.get("connectednessHigh", data.get("connectednessLow", 0.25)),
            deadEndLikelihoodLow=data.get("deadEndLikelihoodLow", 0.7),
            deadEndLikelihoodHigh=data.get("deadEndLikelihoodHigh", data.get("deadEndLikelihoodLow", 0.7)),
            nodeJitterFractionLow=data.get("nodeJitterFractionLow", 0.45),
            nodeJitterFractionHigh=data.get("nodeJitterFractionHigh", data.get("nodeJitterFractionLow", 0.45)),
        )

    def sample_values(self, rng: random.Random | None = None, seed: int | None = None) -> dict[str, float | int | None]:
        rng = rng or random.Random(seed)
        total_nodes = (
            self.totalNodesLow
            if self.totalNodesLow >= self.totalNodesHigh
            else rng.randint(self.totalNodesLow, self.totalNodesHigh)
        )

        def _sample_fraction(low: float, high: float) -> float:
            return low if low >= high else rng.uniform(low, high)

        return {
            "total_nodes": max(1, int(total_nodes)),
            "narrowness": _sample_fraction(self.narrownessLow, self.narrownessHigh),
            "connectedness": _sample_fraction(self.connectednessLow, self.connectednessHigh),
            "dead_end_likelihood": _sample_fraction(self.deadEndLikelihoodLow, self.deadEndLikelihoodHigh),
            "node_jitter_fraction": _sample_fraction(self.nodeJitterFractionLow, self.nodeJitterFractionHigh),
            "seed": seed,
        }

    def summary(self) -> str:
        return (
            f"Nodes {self.totalNodesLow}-{self.totalNodesHigh} | "
            f"Narrowness {self.narrownessLow:.2f}-{self.narrownessHigh:.2f} | "
            f"Connectedness {self.connectednessLow:.2f}-{self.connectednessHigh:.2f} | "
            f"Dead Ends {self.deadEndLikelihoodLow:.2f}-{self.deadEndLikelihoodHigh:.2f} | "
            f"Jitter {self.nodeJitterFractionLow:.2f}-{self.nodeJitterFractionHigh:.2f}"
        )

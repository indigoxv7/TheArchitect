from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import random
import re
from typing import Any
from urllib import error, request


_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class LocalSceneRendererOption:
    key: str
    label: str
    backend: str
    model_name: str = ""

    @property
    def is_tracery(self) -> bool:
        return self.backend == "tracery"


@dataclass(frozen=True)
class LocalSceneRenderResult:
    text: str
    render_state: dict[str, Any]
    node_signature: str
    style_variant: str
    telemetry: dict[str, Any]


class LocalSceneDescriptionService:
    DEFAULT_TRACERY_KEY = "tracery"
    MAX_RECENT_SENTENCES = 8
    MAX_RECENT_OPENINGS = 6
    MAX_RECENT_NODES = 12
    MAX_RECENT_FACTS = 24
    STYLE_VARIANTS: dict[str, str] = {
        "landmark_first": (
            "Lead with the most visually distinctive landmark, then ground the player in the route or affordance."
        ),
        "atmosphere_first": (
            "Open with weather, pressure, or mood before anchoring the player on the clearest physical feature."
        ),
        "movement_first": (
            "Frame the scene in terms of how the squad would move through it, then reveal the landmark details."
        ),
        "evidence_first": (
            "Begin with signs of activity, disturbance, or recent presence, then show the place producing those signs."
        ),
        "contrast_first": (
            "Highlight a striking contrast inside the scene before settling into the concrete layout."
        ),
    }

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        qwen_model: str | None = None,
        gemma_model: str | None = None,
        gpt_oss_model: str | None = None,
        default_runtime_renderer_key: str | None = None,
    ):
        self.base_url = str(base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.timeout_seconds = float(timeout_seconds or os.getenv("OLLAMA_SCENE_TIMEOUT_SECONDS") or 120.0)
        self.qwen_model = str(qwen_model or os.getenv("OLLAMA_LOCAL_SCENE_QWEN_MODEL") or "qwen3:8b").strip()
        self.gemma_model = str(gemma_model or os.getenv("OLLAMA_LOCAL_SCENE_GEMMA_MODEL") or "gemma3:12b").strip()
        self.gpt_oss_model = str(gpt_oss_model or os.getenv("OLLAMA_LOCAL_SCENE_GPT_OSS_MODEL") or "gpt-oss:20b").strip()
        self._default_runtime_renderer_key = str(
            default_runtime_renderer_key or os.getenv("LOCAL_SCENE_RUNTIME_RENDERER_KEY") or f"ollama:{self.qwen_model}"
        ).strip()

    def list_options(self) -> list[LocalSceneRendererOption]:
        return [
            LocalSceneRendererOption(
                key=self.DEFAULT_TRACERY_KEY,
                label="Tracery (Built-in)",
                backend="tracery",
            ),
            LocalSceneRendererOption(
                key=f"ollama:{self.qwen_model}",
                label=f"Ollama - {self.qwen_model}",
                backend="ollama",
                model_name=self.qwen_model,
            ),
            LocalSceneRendererOption(
                key=f"ollama:{self.gemma_model}",
                label=f"Ollama - {self.gemma_model}",
                backend="ollama",
                model_name=self.gemma_model,
            ),
            LocalSceneRendererOption(
                key=f"ollama:{self.gpt_oss_model}",
                label=f"Ollama - {self.gpt_oss_model}",
                backend="ollama",
                model_name=self.gpt_oss_model,
            ),
        ]

    def get_option(self, key: str | None) -> LocalSceneRendererOption | None:
        normalized = str(key or "").strip()
        for option in self.list_options():
            if option.key == normalized:
                return option
        return None

    def default_runtime_option_key(self) -> str:
        preferred = self.get_option(self._default_runtime_renderer_key)
        if preferred is not None:
            return preferred.key
        for option in self.list_options():
            if not option.is_tracery:
                return option.key
        return self.DEFAULT_TRACERY_KEY

    def describe_scene(self, prompt_packet: dict[str, Any], option_key: str) -> str:
        return self.describe_scene_with_history(prompt_packet, option_key, render_state={}).text

    def describe_scene_with_history(
        self,
        prompt_packet: dict[str, Any],
        option_key: str,
        render_state: dict[str, Any] | None = None,
    ) -> LocalSceneRenderResult:
        option = self.get_option(option_key)
        if option is None:
            raise ValueError(f"Unknown local renderer option '{option_key}'.")
        if option.is_tracery:
            raise ValueError("Tracery descriptions are generated in-process and do not use the local LLM service.")

        normalized_state = self._normalize_render_state(render_state)
        canonical_packet = self._canonicalize_prompt_packet(prompt_packet)
        node_signature = self._node_signature(canonical_packet)
        scene_plan = self._plan_scene(canonical_packet, normalized_state, node_signature)
        repetition_risk = self._estimate_repetition_risk(normalized_state, canonical_packet, scene_plan, node_signature)

        if option.backend == "ollama":
            raw_text = self._describe_with_ollama(
                prompt_packet=prompt_packet,
                model_name=option.model_name,
                canonical_packet=canonical_packet,
                scene_plan=scene_plan,
                render_state=normalized_state,
                repetition_risk=repetition_risk,
            )
        else:
            raise ValueError(f"Unsupported local renderer backend '{option.backend}'.")

        final_text = self._repair_scene_text(raw_text, normalized_state)
        updated_state = self._update_render_state(
            normalized_state,
            node_signature=node_signature,
            canonical_packet=canonical_packet,
            scene_plan=scene_plan,
            final_text=final_text,
        )
        telemetry = {
            "repetition_risk": float(repetition_risk),
            "headline_keys": [fact["key"] for fact in scene_plan.get("headlines", [])],
            "headline_labels": [fact["label"] for fact in scene_plan.get("headlines", [])],
            "style_variant": scene_plan.get("style_variant", "landmark_first"),
        }
        return LocalSceneRenderResult(
            text=final_text,
            render_state=updated_state,
            node_signature=node_signature,
            style_variant=str(scene_plan.get("style_variant", "landmark_first") or "landmark_first"),
            telemetry=telemetry,
        )

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return _WHITESPACE_PATTERN.sub(" ", str(value or "")).strip()

    @classmethod
    def _normalize_key(cls, value: Any) -> str:
        return _NON_ALNUM_PATTERN.sub("_", cls._normalize_text(value).lower()).strip("_")

    @staticmethod
    def _sorted_unique_texts(values: list[Any]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for entry in values or []:
            text = _WHITESPACE_PATTERN.sub(" ", str(entry or "")).strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(text)
        normalized.sort(key=lambda item: item.lower())
        return normalized

    def _packet_value(self, payload: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in payload:
                return payload.get(key)
        return None

    def _canonicalize_prompt_packet(self, prompt_packet: dict[str, Any]) -> dict[str, Any]:
        packet = dict(prompt_packet or {})
        setting = dict(packet.get("setting_context") or packet.get("settingContext") or {})
        node = dict(packet.get("node") or {})

        features = []
        for feature in list(node.get("visible_features") or node.get("visibleFeatures") or []):
            if not isinstance(feature, dict):
                continue
            feature_id = self._normalize_text(feature.get("feature_id") or feature.get("featureId") or "")
            category = self._normalize_text(feature.get("category") or "ambient") or "ambient"
            labels = self._sorted_unique_texts(feature.get("visible_labels") or feature.get("visibleLabels") or [])
            if not labels and not feature_id:
                continue
            features.append(
                {
                    "feature_id": feature_id,
                    "category": category,
                    "visible_labels": labels,
                }
            )
        features.sort(key=lambda entry: (entry["category"], entry["feature_id"], ",".join(entry["visible_labels"])))

        hooks = []
        for hook in list(node.get("visible_hooks") or node.get("visibleHooks") or []):
            if not isinstance(hook, dict):
                continue
            hook_id = self._normalize_text(hook.get("hook_id") or hook.get("hookId") or "")
            hook_type = self._normalize_text(hook.get("hook_type") or hook.get("hookType") or "")
            visible_text = self._normalize_text(hook.get("visible_text") or hook.get("visibleText") or "")
            tags = self._sorted_unique_texts(hook.get("tags") or [])
            if not hook_id and not visible_text and not tags:
                continue
            hooks.append(
                {
                    "hook_id": hook_id,
                    "hook_type": hook_type,
                    "visible_text": visible_text,
                    "tags": tags,
                }
            )
        hooks.sort(key=lambda entry: (entry["hook_type"], entry["hook_id"], entry["visible_text"]))

        return {
            "setting": {
                "biome_name": self._normalize_text(self._packet_value(setting, "biomeName", "biome_name")),
                "terrain_name": self._normalize_text(self._packet_value(setting, "terrainName", "terrain_name")),
                "climate_name": self._normalize_text(self._packet_value(setting, "climateName", "climate_name")),
                "setting_tags": self._sorted_unique_texts(
                    setting.get("settingContextTags") or setting.get("setting_context_tags") or []
                ),
                "civilization_tags": self._sorted_unique_texts(setting.get("civilizationTags") or []),
                "threat_tags": self._sorted_unique_texts(setting.get("threatTags") or []),
                "resource_tags": self._sorted_unique_texts(setting.get("resourceTags") or []),
                "mythic_tags": self._sorted_unique_texts(setting.get("mythicTags") or []),
                "ecology_tags": self._sorted_unique_texts(setting.get("ecologyTags") or []),
            },
            "node": {
                "node_id": int(self._packet_value(node, "node_id", "nodeId") or 0),
                "scene_display_name": self._normalize_text(
                    self._packet_value(node, "scene_display_name", "sceneDisplayName")
                ),
                "battle_terrain_label": self._normalize_text(
                    self._packet_value(node, "battle_terrain_label", "battleTerrainLabel")
                ),
                "role_id": self._normalize_text(self._packet_value(node, "role_id", "roleId")),
                "role_name": self._normalize_text(self._packet_value(node, "role_name", "roleName")),
                "role_tags": self._sorted_unique_texts(node.get("role_tags") or node.get("roleTags") or []),
                "feature_tags": self._sorted_unique_texts(node.get("feature_tags") or node.get("featureTags") or []),
                "affordance_tags": self._sorted_unique_texts(
                    node.get("affordance_tags") or node.get("affordanceTags") or []
                ),
                "hook_tags": self._sorted_unique_texts(node.get("hook_tags") or node.get("hookTags") or []),
                "canonical_tags": self._sorted_unique_texts(
                    node.get("canonical_tags") or node.get("canonicalTags") or []
                ),
                "visible_summary_lines": self._sorted_unique_texts(
                    node.get("visible_summary_lines") or node.get("visibleSummaryLines") or []
                ),
                "visible_features": features,
                "visible_hooks": hooks,
            },
        }

    def _node_signature(self, canonical_packet: dict[str, Any]) -> str:
        raw = json.dumps(canonical_packet, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _normalize_render_state(self, render_state: dict[str, Any] | None) -> dict[str, Any]:
        state = dict(render_state or {})
        normalized: dict[str, Any] = {
            "turn": max(0, int(state.get("turn", 0) or 0)),
            "recentNodeSignatures": [],
            "recentFactKeys": [],
            "recentSentenceTexts": [],
            "recentOpeningTexts": [],
            "factRecency": {},
            "styleUses": {},
            "recentStyles": [],
            "phraseHashes": [],
        }

        for entry in list(state.get("recentNodeSignatures") or []):
            if isinstance(entry, dict):
                sig = self._normalize_text(entry.get("signature") or entry.get("sig") or "")
                turn = max(0, int(entry.get("turn", 0) or 0))
            else:
                sig = self._normalize_text(entry)
                turn = normalized["turn"]
            if sig:
                normalized["recentNodeSignatures"].append({"signature": sig, "turn": turn})
        normalized["recentNodeSignatures"] = normalized["recentNodeSignatures"][-self.MAX_RECENT_NODES :]

        for entry in list(state.get("recentFactKeys") or []):
            text = self._normalize_key(entry)
            if text:
                normalized["recentFactKeys"].append(text)
        normalized["recentFactKeys"] = normalized["recentFactKeys"][-self.MAX_RECENT_FACTS :]

        for entry in list(state.get("recentSentenceTexts") or []):
            text = self._normalize_text(entry)
            if text:
                normalized["recentSentenceTexts"].append(text)
        normalized["recentSentenceTexts"] = normalized["recentSentenceTexts"][-self.MAX_RECENT_SENTENCES :]

        for entry in list(state.get("recentOpeningTexts") or []):
            text = self._normalize_text(entry)
            if text:
                normalized["recentOpeningTexts"].append(text)
        normalized["recentOpeningTexts"] = normalized["recentOpeningTexts"][-self.MAX_RECENT_OPENINGS :]

        for key, value in dict(state.get("factRecency") or {}).items():
            fact_key = self._normalize_key(key)
            if not fact_key:
                continue
            payload = dict(value or {}) if isinstance(value, dict) else {}
            normalized["factRecency"][fact_key] = {
                "lastTurn": max(0, int(payload.get("lastTurn", payload.get("last_turn", 0)) or 0)),
                "uses": max(0, int(payload.get("uses", 0) or 0)),
            }

        for key, value in dict(state.get("styleUses") or {}).items():
            style_key = self._normalize_key(key)
            if not style_key:
                continue
            normalized["styleUses"][style_key] = max(0, int(value or 0))

        for entry in list(state.get("recentStyles") or []):
            style_key = self._normalize_key(entry)
            if style_key in self.STYLE_VARIANTS:
                normalized["recentStyles"].append(style_key)
        normalized["recentStyles"] = normalized["recentStyles"][-4:]

        for entry in list(state.get("phraseHashes") or []):
            text = self._normalize_text(entry)
            if text:
                normalized["phraseHashes"].append(text)
        normalized["phraseHashes"] = normalized["phraseHashes"][-self.MAX_RECENT_SENTENCES :]

        return normalized

    def _extract_scene_facts(self, canonical_packet: dict[str, Any]) -> list[dict[str, Any]]:
        node = dict(canonical_packet.get("node") or {})
        setting = dict(canonical_packet.get("setting") or {})
        facts: list[dict[str, Any]] = []

        role_name = self._normalize_text(node.get("role_name", ""))
        if role_name:
            facts.append(
                {
                    "key": f"role:{self._normalize_key(role_name)}",
                    "label": role_name.lower(),
                    "category": "role",
                    "importance": 0.82,
                    "rarity": 0.35,
                }
            )

        for index, feature in enumerate(list(node.get("visible_features") or [])[:4]):
            labels = [self._normalize_text(entry) for entry in feature.get("visible_labels", []) if self._normalize_text(entry)]
            if not labels:
                continue
            primary = labels[0]
            facts.append(
                {
                    "key": f"feature:{self._normalize_key(primary)}",
                    "label": primary.lower(),
                    "category": "landmark" if index == 0 else "feature",
                    "importance": 1.0 if index == 0 else 0.7,
                    "rarity": 0.65 if index == 0 else 0.35,
                }
            )

        for affordance in list(node.get("affordance_tags") or [])[:3]:
            text = self._normalize_text(affordance)
            if not text:
                continue
            facts.append(
                {
                    "key": f"affordance:{self._normalize_key(text)}",
                    "label": text.replace("_", " ").lower(),
                    "category": "affordance",
                    "importance": 0.72,
                    "rarity": 0.28,
                }
            )

        for hook in list(node.get("visible_hooks") or [])[:3]:
            visible_text = self._normalize_text(hook.get("visible_text", ""))
            hook_type = self._normalize_text(hook.get("hook_type", "hook")) or "hook"
            if not visible_text:
                continue
            facts.append(
                {
                    "key": f"hook:{self._normalize_key(hook_type)}:{self._normalize_key(visible_text[:48])}",
                    "label": visible_text,
                    "category": "hook",
                    "importance": 0.62,
                    "rarity": 0.34,
                }
            )

        for key, category, importance in (
            (setting.get("terrain_name", ""), "terrain", 0.42),
            (setting.get("climate_name", ""), "climate", 0.38),
            (setting.get("biome_name", ""), "biome", 0.32),
        ):
            text = self._normalize_text(key)
            if not text:
                continue
            facts.append(
                {
                    "key": f"{category}:{self._normalize_key(text)}",
                    "label": text.lower(),
                    "category": category,
                    "importance": importance,
                    "rarity": 0.18,
                }
            )

        return facts

    def _select_style_variant(self, render_state: dict[str, Any], node_signature: str) -> str:
        recent_styles = list(render_state.get("recentStyles") or [])
        style_uses = dict(render_state.get("styleUses") or {})
        options = []
        for style_key in self.STYLE_VARIANTS:
            uses = int(style_uses.get(style_key, 0) or 0)
            weight = 1.0 / (1.0 + uses)
            if style_key in recent_styles[-2:]:
                weight *= 0.35
            options.append((style_key, max(0.05, weight)))
        total_weight = sum(weight for _style_key, weight in options)
        seed_value = int(hashlib.sha256(f"{node_signature}:{render_state.get('turn', 0)}".encode("utf-8")).hexdigest(), 16)
        rng = random.Random(seed_value)
        threshold = rng.random() * total_weight if total_weight > 0 else 0.0
        running = 0.0
        for style_key, weight in options:
            running += weight
            if running >= threshold:
                return style_key
        return options[0][0] if options else "landmark_first"

    def _plan_scene(self, canonical_packet: dict[str, Any], render_state: dict[str, Any], node_signature: str) -> dict[str, Any]:
        facts = self._extract_scene_facts(canonical_packet)
        fact_recency = dict(render_state.get("factRecency") or {})
        recent_fact_keys = list(render_state.get("recentFactKeys") or [])
        recent_node_signatures = [entry.get("signature", "") for entry in list(render_state.get("recentNodeSignatures") or [])]
        signature_visit_count = sum(1 for entry in recent_node_signatures if entry == node_signature)

        scored: list[dict[str, Any]] = []
        for fact in facts:
            fact_key = str(fact.get("key", "") or "")
            recency_payload = dict(fact_recency.get(fact_key) or {})
            recency_penalty = 1.0 if fact_key in recent_fact_keys[-4:] else 0.0
            if recency_payload:
                turns_since = max(0, int(render_state.get("turn", 0) or 0) - int(recency_payload.get("lastTurn", 0) or 0))
                recency_penalty = max(recency_penalty, 0.5 ** (turns_since / 3.0) if turns_since >= 0 else 1.0)
            uses = int(recency_payload.get("uses", 0) or 0)
            global_overuse = min(1.0, uses / 5.0)
            novelty = 1.0 - min(1.0, (0.25 * signature_visit_count) + (0.2 * recency_penalty))
            score = (
                1.4 * float(fact.get("importance", 0.0) or 0.0)
                + 0.8 * float(fact.get("rarity", 0.0) or 0.0)
                + 0.9 * novelty
                - 1.0 * recency_penalty
                - 0.6 * global_overuse
            )
            scored.append({**fact, "score": score})

        scored.sort(key=lambda entry: float(entry.get("score", 0.0)), reverse=True)
        headlines: list[dict[str, Any]] = []
        category_counts: dict[str, int] = {}
        for fact in scored:
            category = str(fact.get("category", "misc") or "misc")
            if category == "landmark" and category_counts.get("landmark", 0) >= 1:
                continue
            if category == "hook" and category_counts.get("hook", 0) >= 1:
                continue
            if category == "affordance" and category_counts.get("affordance", 0) >= 1:
                continue
            headlines.append(fact)
            category_counts[category] = category_counts.get(category, 0) + 1
            if len(headlines) >= 3:
                break
        if not any(entry.get("category") == "affordance" for entry in headlines):
            affordance = next((entry for entry in scored if entry.get("category") == "affordance"), None)
            if affordance is not None and affordance not in headlines:
                if len(headlines) >= 3:
                    headlines[-1] = affordance
                else:
                    headlines.append(affordance)

        supporting = [entry for entry in scored if entry not in headlines][:4]
        style_variant = self._select_style_variant(render_state, node_signature)
        return {
            "headlines": headlines,
            "supporting": supporting,
            "style_variant": style_variant,
            "style_instruction": self.STYLE_VARIANTS.get(style_variant, self.STYLE_VARIANTS["landmark_first"]),
        }

    def _estimate_repetition_risk(
        self,
        render_state: dict[str, Any],
        canonical_packet: dict[str, Any],
        scene_plan: dict[str, Any],
        node_signature: str,
    ) -> float:
        recent_node_signatures = [entry.get("signature", "") for entry in list(render_state.get("recentNodeSignatures") or [])]
        signature_visit_count = sum(1 for entry in recent_node_signatures if entry == node_signature)
        headline_keys = [str(fact.get("key", "") or "") for fact in scene_plan.get("headlines", [])]
        recent_fact_keys = set(render_state.get("recentFactKeys") or [])
        repeated_headlines = sum(1 for key in headline_keys if key in recent_fact_keys)
        recent_openings = list(render_state.get("recentOpeningTexts") or [])
        role_name = self._normalize_text(canonical_packet.get("node", {}).get("role_name", ""))
        role_risk = 0.15 if role_name and any(role_name.lower() in entry.lower() for entry in recent_openings[-2:]) else 0.0
        risk = (0.25 * min(1.0, signature_visit_count / 2.0)) + (0.2 * min(1.0, repeated_headlines / 2.0)) + role_risk
        return max(0.0, min(1.0, risk))

    def _describe_with_ollama(
        self,
        prompt_packet: dict[str, Any],
        model_name: str,
        canonical_packet: dict[str, Any],
        scene_plan: dict[str, Any],
        render_state: dict[str, Any],
        repetition_risk: float,
    ) -> str:
        recent_sentences = list(render_state.get("recentSentenceTexts") or [])[-4:]
        recent_openings = list(render_state.get("recentOpeningTexts") or [])[-3:]
        system_prompt = (
            "Write a short arrival description for a mission node in a fantasy tactics game. "
            "Use only the supplied structured packet and scene plan. "
            "Do not mention hidden hazards, unobserved threats, or unseen treasure. "
            "Keep it to 2-4 sentences, concrete, sensory, and useful at the table. "
            "Vary sentence structure and opening rhythm so multiple nearby nodes do not read the same."
        )
        user_payload = {
            "scene_plan": {
                "style_variant": scene_plan.get("style_variant", "landmark_first"),
                "style_instruction": scene_plan.get("style_instruction", self.STYLE_VARIANTS["landmark_first"]),
                "headline_facts": [
                    {
                        "label": fact.get("label", ""),
                        "category": fact.get("category", "misc"),
                        "importance": fact.get("importance", 0.0),
                    }
                    for fact in scene_plan.get("headlines", [])
                ],
                "supporting_facts": [fact.get("label", "") for fact in scene_plan.get("supporting", [])],
            },
            "recent_avoidance": {
                "avoid_exact_sentences": recent_sentences,
                "avoid_opening_patterns": recent_openings,
            },
            "canonical_scene": canonical_packet,
        }
        payload = {
            "model": str(model_name or "").strip(),
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "options": self._decode_options(repetition_risk),
        }
        request_body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/api/chat",
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            try:
                details = exc.read().decode("utf-8")
            except Exception:
                details = str(exc)
            raise RuntimeError(f"Ollama returned HTTP {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(
                f"Could not reach Ollama at {self.base_url}. Start Ollama and make sure the local API is available."
            ) from exc

        if isinstance(raw, dict) and raw.get("error"):
            raise RuntimeError(str(raw.get("error")))
        text = ""
        if isinstance(raw, dict):
            message = raw.get("message", {})
            if isinstance(message, dict):
                text = str(message.get("content", "") or "")
        text = text.strip()
        if not text:
            raise RuntimeError("Ollama did not return any scene description text.")
        return text

    def _decode_options(self, repetition_risk: float) -> dict[str, Any]:
        risk = max(0.0, min(1.0, float(repetition_risk or 0.0)))
        return {
            "temperature": round(0.75 + (0.1 * risk), 3),
            "top_p": round(0.9 - (0.02 * risk), 3),
            "top_k": 40,
            "typical_p": round(1.0 - (0.1 * risk), 3),
            "repeat_penalty": round(1.12 + (0.08 * risk), 3),
            "repeat_last_n": 128 if risk >= 0.35 else 96,
            "num_ctx": 4096,
        }

    def _repair_scene_text(self, text: str, render_state: dict[str, Any]) -> str:
        cleaned = self._normalize_text(text).strip('"')
        if not cleaned:
            raise RuntimeError("Local scene description came back empty after cleanup.")
        raw_sentences = [sentence.strip() for sentence in _SENTENCE_SPLIT_PATTERN.split(cleaned) if sentence.strip()]
        recent_sentence_keys = {self._normalize_key(entry) for entry in list(render_state.get("recentSentenceTexts") or [])}
        deduped: list[str] = []
        seen_sentence_keys: set[str] = set()
        for sentence in raw_sentences:
            key = self._normalize_key(sentence)
            if not key or key in seen_sentence_keys:
                continue
            if key in recent_sentence_keys and len(raw_sentences) > 1:
                continue
            seen_sentence_keys.add(key)
            deduped.append(sentence)
        if not deduped:
            deduped = raw_sentences[:1]
        deduped = deduped[:4]
        repaired = " ".join(deduped).strip()
        repaired = repaired.replace("..", ".")
        return repaired

    def _update_render_state(
        self,
        render_state: dict[str, Any],
        *,
        node_signature: str,
        canonical_packet: dict[str, Any],
        scene_plan: dict[str, Any],
        final_text: str,
    ) -> dict[str, Any]:
        updated = self._normalize_render_state(render_state)
        updated["turn"] = int(updated.get("turn", 0) or 0) + 1
        turn = int(updated["turn"])

        updated["recentNodeSignatures"].append({"signature": node_signature, "turn": turn})
        updated["recentNodeSignatures"] = updated["recentNodeSignatures"][-self.MAX_RECENT_NODES :]

        sentences = [sentence.strip() for sentence in _SENTENCE_SPLIT_PATTERN.split(final_text) if sentence.strip()]
        for sentence in sentences[:4]:
            updated["recentSentenceTexts"].append(sentence)
            updated["phraseHashes"].append(hashlib.sha1(self._normalize_text(sentence).encode("utf-8")).hexdigest())
        updated["recentSentenceTexts"] = updated["recentSentenceTexts"][-self.MAX_RECENT_SENTENCES :]
        updated["phraseHashes"] = updated["phraseHashes"][-self.MAX_RECENT_SENTENCES :]

        if sentences:
            updated["recentOpeningTexts"].append(sentences[0])
            updated["recentOpeningTexts"] = updated["recentOpeningTexts"][-self.MAX_RECENT_OPENINGS :]

        for fact in scene_plan.get("headlines", []) + scene_plan.get("supporting", []):
            fact_key = self._normalize_key(fact.get("key", ""))
            if not fact_key:
                continue
            updated["recentFactKeys"].append(fact_key)
            payload = dict(updated["factRecency"].get(fact_key) or {})
            payload["lastTurn"] = turn
            payload["uses"] = int(payload.get("uses", 0) or 0) + 1
            updated["factRecency"][fact_key] = payload
        updated["recentFactKeys"] = updated["recentFactKeys"][-self.MAX_RECENT_FACTS :]

        style_variant = self._normalize_key(scene_plan.get("style_variant", "landmark_first")) or "landmark_first"
        updated["styleUses"][style_variant] = int(updated["styleUses"].get(style_variant, 0) or 0) + 1
        updated["recentStyles"].append(style_variant)
        updated["recentStyles"] = updated["recentStyles"][-4:]

        return updated

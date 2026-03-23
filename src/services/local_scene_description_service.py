from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib import error, request


@dataclass(frozen=True)
class LocalSceneRendererOption:
    key: str
    label: str
    backend: str
    model_name: str = ""

    @property
    def is_tracery(self) -> bool:
        return self.backend == "tracery"


class LocalSceneDescriptionService:
    DEFAULT_TRACERY_KEY = "tracery"

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        qwen_model: str | None = None,
        gemma_model: str | None = None,
        gpt_oss_model: str | None = None,
    ):
        self.base_url = str(base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.timeout_seconds = float(timeout_seconds or os.getenv("OLLAMA_SCENE_TIMEOUT_SECONDS") or 120.0)
        self.qwen_model = str(qwen_model or os.getenv("OLLAMA_LOCAL_SCENE_QWEN_MODEL") or "qwen3:8b").strip()
        self.gemma_model = str(gemma_model or os.getenv("OLLAMA_LOCAL_SCENE_GEMMA_MODEL") or "gemma3:12b").strip()
        self.gpt_oss_model = str(gpt_oss_model or os.getenv("OLLAMA_LOCAL_SCENE_GPT_OSS_MODEL") or "gpt-oss:20b").strip()

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

    def describe_scene(self, prompt_packet: dict[str, Any], option_key: str) -> str:
        option = self.get_option(option_key)
        if option is None:
            raise ValueError(f"Unknown local renderer option '{option_key}'.")
        if option.is_tracery:
            raise ValueError("Tracery descriptions are generated in-process and do not use the local LLM service.")
        if option.backend == "ollama":
            return self._describe_with_ollama(prompt_packet, option.model_name)
        raise ValueError(f"Unsupported local renderer backend '{option.backend}'.")

    def _describe_with_ollama(self, prompt_packet: dict[str, Any], model_name: str) -> str:
        payload = {
            "model": str(model_name or "").strip(),
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Write a short arrival description for a mission node in a fantasy tactics game. "
                        "Use only the supplied structured packet. Do not invent canon-breaking details. "
                        "Keep it concise, concrete, and sensory."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt_packet, ensure_ascii=False),
                },
            ],
            "options": {
                "temperature": 0.2,
                "num_ctx": 4096,
            },
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

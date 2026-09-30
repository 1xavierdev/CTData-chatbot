"""Minimal client for LM Studio's OpenAI-compatible local server.

Start the server in LM Studio (Developer tab -> Start Server, default port 1234)
and load one chat model plus one embedding model. Override with env vars:

    LMSTUDIO_URL   default http://localhost:1234/v1
    CHAT_MODEL     default: the first non-embedding model LM Studio has loaded
    EMBED_MODEL    default text-embedding-nomic-embed-text-v1.5
"""

from __future__ import annotations

import os
import re

import requests

BASE_URL = os.environ.get("LMSTUDIO_URL", "http://localhost:1234/v1").rstrip("/")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "")
TIMEOUT = float(os.environ.get("LMSTUDIO_TIMEOUT", "120"))


def list_models() -> list[str] | None:
    try:
        resp = requests.get(f"{BASE_URL}/models", timeout=3)
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]
    except (requests.RequestException, ValueError):
        return None


def chat_model() -> str | None:
    if CHAT_MODEL:
        return CHAT_MODEL
    models = list_models() or []
    return next((m for m in models if "embed" not in m.lower()), None)


def embed(texts: list[str]) -> list[list[float]] | None:
    """Return one vector per text, or None if LM Studio isn't reachable."""
    try:
        resp = requests.post(f"{BASE_URL}/embeddings", json={"model": EMBED_MODEL, "input": texts}, timeout=TIMEOUT)
        resp.raise_for_status()
        return [d["embedding"] for d in sorted(resp.json()["data"], key=lambda d: d["index"])]
    except (requests.RequestException, KeyError, ValueError):
        return None


def chat(messages: list[dict], temperature: float = 0.3) -> str | None:
    """Return the assistant reply, or None if no chat model is available."""
    model = chat_model()
    if not model:
        return None
    try:
        resp = requests.post(
            f"{BASE_URL}/chat/completions",
            json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": 700},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"] or ""
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None
    # Reasoning models (Qwen3, DeepSeek-R1 distills) may include their thinking; hide it.
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

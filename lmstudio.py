"""Minimal client for LM Studio's OpenAI-compatible local server.

Start the server in LM Studio (Developer tab -> Start Server, default port 1234)
and load one chat model plus one embedding model. Override with env vars:

    LMSTUDIO_URL   default http://localhost:1234/v1
    CHAT_MODEL     default: the first non-embedding model LM Studio has loaded
    EMBED_MODEL    default text-embedding-nomic-embed-text-v1.5
"""

from __future__ import annotations

import json
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


def loaded_chat_models() -> list[str]:
    """Chat models LM Studio currently has in memory (its native API; /v1/models also lists unloaded ones)."""
    try:
        resp = requests.get(f"{BASE_URL.rsplit('/v1', 1)[0]}/api/v0/models", timeout=3)
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])
                if m.get("state") == "loaded" and m.get("type") in {"llm", "vlm"}]
    except (requests.RequestException, ValueError, KeyError):
        return []


def chat_model() -> str | None:
    if CHAT_MODEL:
        return CHAT_MODEL
    # Prefer a loaded model: picking an unloaded one makes LM Studio load it on demand,
    # which for a model too big for the machine means minutes of swapping.
    if loaded := loaded_chat_models():
        return loaded[0]
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


def chat(messages: list[dict], temperature: float = 0.3, **options) -> str | None:
    """Return the assistant reply, or None if no chat model is available or it didn't answer in time."""
    model = chat_model()
    if not model:
        print("LM Studio: no chat model loaded")
        return None
    # Reasoning models (Qwen3, Qwen3.5, ...) "think" before answering by default, which can use the
    # whole token budget and minutes on a laptop. reasoning_effort "none" turns that off in LM Studio;
    # Qwen3 (but not 3.5) also needs the /no_think switch in the prompt.
    if re.search(r"qwen3(?!\.)", model.lower()):
        messages = [*messages[:-1], {**messages[-1], "content": messages[-1]["content"] + "\n/no_think"}]
    try:
        resp = requests.post(
            f"{BASE_URL}/chat/completions",
            json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": 700,
                  "reasoning_effort": "none", **options},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"] or ""
    except requests.Timeout:
        print(f"LM Studio: {model} did not answer within {TIMEOUT:.0f}s (model too large for this machine?)")
        return None
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        print(f"LM Studio: chat request failed: {exc}")
        return None
    # Reasoning models (Qwen3, DeepSeek-R1 distills) may include their thinking; hide it.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text or None


def chat_json(messages: list[dict], schema: dict) -> dict | None:
    """Like chat(), but LM Studio constrains the reply to JSON matching `schema`."""
    reply = chat(messages, temperature=0, response_format={
        "type": "json_schema", "json_schema": {"name": "reply", "strict": True, "schema": schema}})
    try:
        return json.loads(reply) if reply else None
    except ValueError:
        return None

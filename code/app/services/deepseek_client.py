from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"


class DeepSeekError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY"))


def is_enabled() -> bool:
    return os.environ.get("AGENT_MODE", "local").strip().lower() in {"deepseek", "llm", "api"}


def chat_completion(
    messages: list[dict[str, str]],
    *,
    response_format: dict[str, str] | None = None,
    max_tokens: int = 1200,
    temperature: float = 0.2,
) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise DeepSeekError("DEEPSEEK_API_KEY is not set")

    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL)
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking": {"type": "disabled"},
    }
    if response_format:
        payload["response_format"] = response_format

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    opener = _build_opener()

    try:
        with opener.open(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise DeepSeekError(f"DeepSeek API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise DeepSeekError(f"DeepSeek API request failed: {exc.reason}") from exc

    try:
        body = json.loads(raw)
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise DeepSeekError(f"Unexpected DeepSeek API response: {raw[:500]}") from exc


def _build_opener() -> urllib.request.OpenerDirector:
    proxy = os.environ.get("DEEPSEEK_PROXY", "").strip()
    if proxy:
        return urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener()

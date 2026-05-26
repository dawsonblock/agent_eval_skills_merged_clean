from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx


class DeepSeekClientError(RuntimeError):
    """Base error for DeepSeek client failures."""


class DeepSeekAuthError(DeepSeekClientError):
    """Raised when authentication details are missing or rejected."""


class DeepSeekClient:
    """Async client for DeepSeek's OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self._base_url = (
            base_url or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        ).rstrip("/")
        self._model = model or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(0, max_retries)

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    @property
    def default_model(self) -> str:
        return self._model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
        model: str | None = None,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise DeepSeekAuthError(
                "DeepSeek API key is not configured. Set DEEPSEEK_API_KEY in your environment."
            )

        payload: dict[str, Any] = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        attempt = 0
        while True:
            try:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                return self._handle_response(response)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= self._max_retries:
                    raise DeepSeekClientError(
                        f"DeepSeek request failed after retries: {exc.__class__.__name__}"
                    ) from exc
                await asyncio.sleep(0.5 * (2**attempt))
                attempt += 1

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code in (401, 403):
            raise DeepSeekAuthError("DeepSeek authentication failed. Check DEEPSEEK_API_KEY.")
        if response.status_code >= 500:
            raise DeepSeekClientError(
                f"DeepSeek server error (status {response.status_code}). Please retry later."
            )
        if response.status_code >= 400:
            detail = self._safe_error_detail(response)
            raise DeepSeekClientError(
                f"DeepSeek request rejected (status {response.status_code}): {detail}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise DeepSeekClientError("DeepSeek returned a non-JSON response.") from exc

        if not isinstance(data, dict):
            raise DeepSeekClientError("DeepSeek returned malformed JSON payload.")

        choices = data.get("choices") or []
        message: dict[str, Any] = {}
        if choices and isinstance(choices, list) and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}

        return {
            "id": data.get("id"),
            "model": data.get("model") or self._model,
            "message": message,
            "tool_calls": message.get("tool_calls") if isinstance(message, dict) else None,
            "raw": data,
        }

    @staticmethod
    def _safe_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                err = payload.get("error")
                if isinstance(err, dict):
                    msg = err.get("message")
                    if isinstance(msg, str) and msg.strip():
                        return msg.strip()
        except Exception:
            pass
        text = response.text.strip()
        if not text:
            return "No details provided"
        return text[:300]

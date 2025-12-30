"""Async streaming Ollama client."""

import asyncio
import json
import httpx
from typing import Awaitable, Callable, Optional

from ..config import settings


# Global lock to ensure only one Ollama request at a time
_ollama_lock = asyncio.Lock()


SYSTEM_PROMPT = """You are an expert poker player. Analyze and decide the optimal action.

Output format: <action>ACTION</action>
- <action>f</action> = fold
- <action>cc</action> = call/check
- <action>cbr AMOUNT</action> = bet/raise to AMOUNT

Think step by step about your decision, then output ONE action tag at the end."""


class OllamaStreamingClient:
    """Async streaming client for Ollama API."""

    def __init__(
        self,
        endpoint: str = settings.ollama_endpoint,
        timeout: float = settings.ollama_timeout,
    ):
        self.endpoint = endpoint
        self.timeout = timeout

    async def check_connection(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.endpoint}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[dict]:
        """List available Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.endpoint}/api/tags")
                if response.status_code == 200:
                    return response.json().get("models", [])
        except Exception:
            pass
        return []

    async def generate_streaming(
        self,
        model: str,
        prompt: str,
        on_token: Callable[[str], Awaitable[None]],
        temperature: float = 0.6,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate response with streaming tokens.

        Args:
            model: Ollama model name
            prompt: User prompt
            on_token: Async callback for each token
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            system_prompt: Optional custom system prompt

        Returns:
            Complete response text
        """
        # Acquire global lock to ensure only one Ollama request at a time
        async with _ollama_lock:
            return await self._generate_streaming_impl(
                model, prompt, on_token, temperature, max_tokens, system_prompt
            )

    async def _generate_streaming_impl(
        self,
        model: str,
        prompt: str,
        on_token: Callable[[str], Awaitable[None]],
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str],
    ) -> str:
        """Internal implementation of streaming generation."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        full_response = ""

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.endpoint}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # Handle regular content
                        content = data.get("message", {}).get("content", "")
                        if content:
                            full_response += content
                            await on_token(content)

                        # Handle thinking content (for thinking models like qwen3)
                        thinking = data.get("message", {}).get("thinking", "")
                        if thinking:
                            full_response += thinking
                            await on_token(thinking)

                        # Check if done
                        if data.get("done", False):
                            break

                    except json.JSONDecodeError:
                        continue

        return full_response

    async def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.6,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate response without streaming (for simple use cases).

        Args:
            model: Ollama model name
            prompt: User prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            system_prompt: Optional custom system prompt

        Returns:
            Complete response text
        """
        # Acquire global lock to ensure only one Ollama request at a time
        async with _ollama_lock:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.endpoint}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()

                msg = result.get("message", {})
                content = msg.get("content", "")
                thinking = msg.get("thinking", "")

                return content if content else thinking

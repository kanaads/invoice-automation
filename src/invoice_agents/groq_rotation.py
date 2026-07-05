"""ChatGroq subclass that rotates through multiple API keys when one hits its rate limit."""
import time

from langchain_groq import ChatGroq
from pydantic import SecretStr

WAIT_SECONDS = 60
MAX_WAIT_CYCLES = 5


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc).lower()
    return "rate_limit" in text or "429" in text or type(exc).__name__ == "RateLimitError"


class RotatingChatGroq(ChatGroq):
    def __init__(self, api_keys: list[str], **kwargs):
        if not api_keys:
            raise ValueError("RotatingChatGroq requires at least one API key")
        super().__init__(api_key=api_keys[0], **kwargs)
        object.__setattr__(self, "_rotation_keys", list(api_keys))
        object.__setattr__(self, "_rotation_index", 0)

    def _swap_key(self) -> None:
        import groq

        self._rotation_index = (self._rotation_index + 1) % len(self._rotation_keys)
        next_key = self._rotation_keys[self._rotation_index]
        self.groq_api_key = SecretStr(next_key)
        self.client = groq.Groq(api_key=next_key).chat.completions
        self.async_client = groq.AsyncGroq(api_key=next_key).chat.completions

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        last_exc: Exception | None = None
        for cycle in range(MAX_WAIT_CYCLES):
            for _ in range(len(self._rotation_keys)):
                try:
                    return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
                except Exception as exc:  # noqa: BLE001 -- rotate on rate limit, re-raise anything else
                    if not _is_rate_limit(exc):
                        raise
                    last_exc = exc
                    self._swap_key()
            if cycle < MAX_WAIT_CYCLES - 1:
                time.sleep(WAIT_SECONDS)
        assert last_exc is not None
        raise last_exc

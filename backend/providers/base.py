"""Base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Literal, Optional


@dataclass(frozen=True)
class ProviderStreamEvent:
    """A provider-neutral, user-visible streaming event."""

    type: Literal["text_delta", "completed", "error"]
    delta: str = ""
    result: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def query(self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Send a query to the LLM.
        
        Args:
            model_id: The ID of the model to query.
            messages: List of message dicts (role, content).
            timeout: Request timeout in seconds.
            
        Returns:
            Dict containing 'content' (str) or 'error' (bool) and 'error_message' (str).
        """
        pass

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider implements incremental response streaming."""
        return False

    async def stream_query(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0,
        temperature: float = 0.7,
    ) -> AsyncIterator[ProviderStreamEvent]:
        """Stream a response when supported; callers must capability-check first."""
        raise NotImplementedError(f"{type(self).__name__} does not support streaming")
        yield  # pragma: no cover - makes this an async generator

    @abstractmethod
    async def get_models(self) -> List[Dict[str, Any]]:
        """
        Fetch available models from the provider.
        
        Returns:
            List of model dicts (id, name, context_length, etc.).
        """
        pass

    @abstractmethod
    async def validate_key(self, api_key: str) -> Dict[str, Any]:
        """
        Validate the provided API key.
        
        Args:
            api_key: The API key to test.
            
        Returns:
            Dict with 'success' (bool) and 'message' (str).
        """
        pass

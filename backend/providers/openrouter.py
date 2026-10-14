"""OpenRouter provider wrapper."""

from typing import Dict, Any, List, Optional, Tuple
from .base import LLMProvider
from .. import openrouter
from ..credentials import get_api_key

# In-memory per-token USD pricing, keyed by the bare OpenRouter model id
# (e.g. "anthropic/claude-3.5-sonnet"). Populated/refreshed on every
# successful get_models() fetch; the last successful fetch wins. A fresh app
# state starts with an empty cache until the model list is first fetched, so
# pricing is simply unavailable for any model not yet cached rather than guessed.
_PRICING: Dict[str, Dict[str, float]] = {}


def _bare_model_id(model_id: str) -> str:
    """Strip the internal ``openrouter:`` prefix to the upstream model id."""
    if model_id.startswith("openrouter:"):
        return model_id[len("openrouter:"):]
    return model_id


def compute_openrouter_cost_usd(model_id: str, usage: Optional[Dict[str, Any]]) -> Optional[float]:
    """Return USD cost for an OpenRouter-routed model, or None when not computable.

    Cost is only ever computed when ALL of the following hold:
      * the model id is ``openrouter:``-prefixed,
      * per-token pricing for the bare model id was successfully cached,
      * ``usage`` carries real, non-negative ``prompt_tokens`` and
        ``completion_tokens``.
    Otherwise ``None`` is returned so the caller leaves ``cost_usd`` absent
    (never ``0``, never guessed).
    """
    if not usage or not isinstance(usage, dict):
        return None
    if not model_id.startswith("openrouter:"):
        return None
    price = _PRICING.get(_bare_model_id(model_id))
    if price is None:
        return None
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    if not isinstance(prompt_tokens, (int, float)) or not isinstance(completion_tokens, (int, float)):
        return None
    if prompt_tokens < 0 or completion_tokens < 0:
        return None
    return prompt_tokens * price["prompt"] + completion_tokens * price["completion"]


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider."""
    
    async def query(self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7) -> Dict[str, Any]:
        # Strip internal prefix if present
        if model_id.startswith("openrouter:"):
            model_id = model_id.replace("openrouter:", "", 1)
            
        # OpenRouter module handles key retrieval internally
        return await openrouter.query_model(model_id, messages, timeout, temperature)

    async def get_models(self) -> List[Dict[str, Any]]:
        # We can reuse the existing endpoint logic or implement a direct fetch here
        # For now, let's implement a direct fetch to match the interface pattern
        import httpx
        api_key = get_api_key("openrouter")
        
        if not api_key:
            return []
            
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                
                if response.status_code != 200:
                    return []
                    
                data = response.json()
                models = []
                for model in data.get("data", []):
                    # Filter out non-chat models based on ID and Name
                    mid = model.get("id", "").lower()
                    name = model.get("name", "").lower()
                    
                    # Comprehensive exclusion list for non-text/chat models
                    excluded_terms = [
                        "embed", "audio", "whisper", "tts", "dall-e", "realtime", 
                        "vision-only", "voxtral", "speech", "transcribe", "sora"
                    ]
                    
                    if any(term in mid for term in excluded_terms) or any(term in name for term in excluded_terms):
                        continue
                        
                    # Extract pricing
                    pricing = model.get("pricing", {})
                    prompt_price = float(pricing.get("prompt", "0") or "0")
                    completion_price = float(pricing.get("completion", "0") or "0")
                    is_free = prompt_price == 0 and completion_price == 0
                    _PRICING[model.get("id")] = {
                        "prompt": prompt_price,
                        "completion": completion_price,
                    }

                    models.append({
                        "id": f"openrouter:{model.get('id')}",
                        "name": f"{model.get('name', model.get('id'))} [OpenRouter]",
                        "provider": "OpenRouter",
                        "is_free": is_free,
                        "prompt_price_per_token": prompt_price,
                        "completion_price_per_token": completion_price,
                    })
                return sorted(models, key=lambda x: x["name"])
        except Exception:
            return []

    async def validate_key(self, api_key: str) -> Dict[str, Any]:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "API key is valid"}
                elif response.status_code == 401:
                    return {"success": False, "message": "Invalid API key"}
                else:
                    return {"success": False, "message": f"API error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

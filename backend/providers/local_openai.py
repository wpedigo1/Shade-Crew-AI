"""Named anonymous OpenAI-compatible servers, including FOB llama.cpp.

Authenticated endpoints continue to use the existing custom provider and
credential store. Local endpoint settings never contain or borrow API keys.
"""
import asyncio
import json
from weakref import WeakValueDictionary

import httpx

from .base import ProviderStreamEvent
from .custom_openai import CustomOpenAIProvider
from ..settings import get_settings


# Hold one local server's model resident until its request finishes. Different
# endpoints remain independent. Weak values avoid retaining finished event loops.
_endpoint_locks = WeakValueDictionary()


def _endpoint_lock(url):
    key = (asyncio.get_running_loop(), url)
    lock = _endpoint_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _endpoint_locks[key] = lock
    return lock


class LocalOpenAIProvider(CustomOpenAIProvider):
    def __init__(self, endpoint_id: str):
        self.endpoint_id = endpoint_id

    def _get_config(self):
        endpoint = next((e for e in get_settings().local_endpoints
                         if e.id == self.endpoint_id and e.enabled), None)
        if endpoint is None:
            raise ValueError(f"Local endpoint {self.endpoint_id!r} is missing or disabled")
        return endpoint.name, endpoint.url, ""

    def _model(self, model_id):
        prefix = f"local:{self.endpoint_id}:"
        if not model_id.startswith(prefix) or not model_id[len(prefix):]:
            raise ValueError("Model ID does not belong to this local endpoint")
        return model_id[len(prefix):]

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        config = self._get_config()
        async with _endpoint_lock(config[1]):
            return await self._query_with_config(f"custom:{self._model(model_id)}", messages, timeout, temperature, config)

    async def get_models(self):
        models = await super().get_models()
        for model in models:
            model['id'] = f"local:{self.endpoint_id}:{model['id'].removeprefix('custom:')}"
        return models

    @property
    def supports_streaming(self):
        return True

    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        config = self._get_config()
        async with _endpoint_lock(config[1]):
            stream = self._stream_query(model_id, messages, timeout, temperature, config)
            try:
                async for event in stream:
                    yield event
            finally:
                await stream.aclose()

    async def _stream_query(self, model_id, messages, timeout, temperature, config):
        model = self._model(model_id)
        name, base_url, _ = config
        usage = None
        finish_reason = None
        finished = False
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    'POST', f'{base_url}/chat/completions',
                    json={'model': model, 'messages': messages, 'temperature': temperature,
                          'stream': True, 'stream_options': {'include_usage': True}},
                ) as response:
                    if response.status_code != 200:
                        yield ProviderStreamEvent(type='error', error_message=f'{name} API error: {response.status_code}')
                        return
                    async for line in response.aiter_lines():
                        if not line.startswith('data:'):
                            continue
                        data = line[5:].strip()
                        if data == '[DONE]':
                            finished = True
                            break
                        if not data:
                            continue
                        chunk = json.loads(data)
                        reported_model = chunk.get('model')
                        if reported_model is not None and reported_model != model:
                            yield ProviderStreamEvent(type='error', error_message=f'{name} model identity mismatch: requested {model!r}, received {reported_model!r}')
                            return
                        if chunk.get('error'):
                            yield ProviderStreamEvent(type='error', error_message=f'{name} stream reported an error')
                            return
                        if chunk.get('usage') is not None:
                            usage = chunk['usage']
                        for choice in chunk.get('choices', []):
                            # Only visible content is forwarded; reasoning_content is excluded.
                            content = (choice.get('delta') or {}).get('content')
                            if content:
                                yield ProviderStreamEvent(type='text_delta', delta=content)
                            if choice.get('finish_reason') is not None:
                                finish_reason = choice['finish_reason']
                                finished = True
            if not finished:
                yield ProviderStreamEvent(type='error', error_message=f'{name} stream ended without a completion marker')
                return
            yield ProviderStreamEvent(type='completed', usage=usage, finish_reason=finish_reason)
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            # Preserve canonical worker/Moderator timeout classification.
            raise asyncio.TimeoutError from exc
        except httpx.ConnectError:
            yield ProviderStreamEvent(type='error', error_message=f'{name} connection failed')
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            yield ProviderStreamEvent(type='error', error_message=f'{name} invalid or interrupted stream ({type(exc).__name__})')

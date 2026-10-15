"""Named local endpoints preserve routing and visible streaming without cloud fallback."""
import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from backend.settings import Settings
from backend.providers.local_openai import LocalOpenAIProvider
from backend.council import get_provider_for_model


def endpoint(endpoint_id='fob-a', **kwargs):
    return {'id': endpoint_id, 'name': 'FOB A', 'url': 'http://127.0.0.1:18081/v1/', **kwargs}


@pytest.fixture
def local_settings(monkeypatch):
    settings = Settings(local_endpoints=[endpoint(), endpoint('fob-b', name='FOB B', url='http://127.0.0.1:18082/v1')])
    monkeypatch.setattr('backend.providers.local_openai.get_settings', lambda: settings)
    return settings


def test_endpoint_configuration_validation():
    assert Settings(local_endpoints=[endpoint()]).local_endpoints[0].url == 'http://127.0.0.1:18081/v1'
    for bad in [endpoint(id='bad:id'), endpoint(url='file:///tmp/models'), endpoint(url='http://user:secret@localhost/v1'), endpoint(api_key='secret'), endpoint(url='http://localhost/v1?token=secret')]:
        with pytest.raises(ValidationError):
            Settings(local_endpoints=[bad])
    with pytest.raises(ValidationError):
        Settings(local_endpoints=[endpoint(), endpoint()])


@respx.mock
async def test_discovery_keeps_endpoint_identity_for_same_model(local_settings):
    respx.get('http://127.0.0.1:18081/v1/models').mock(return_value=httpx.Response(200, json={'data': [{'id': 'same:model'}]}))
    respx.get('http://127.0.0.1:18082/v1/models').mock(return_value=httpx.Response(200, json={'data': [{'id': 'same:model'}]}))
    a = await LocalOpenAIProvider('fob-a').get_models()
    b = await LocalOpenAIProvider('fob-b').get_models()
    assert a[0]['id'] == 'local:fob-a:same:model'
    assert b[0]['id'] == 'local:fob-b:same:model'
    assert a[0]['provider'] == 'FOB A'


@respx.mock
async def test_query_uses_exact_model_and_no_credential(local_settings):
    route = respx.post('http://127.0.0.1:18082/v1/chat/completions').mock(return_value=httpx.Response(200, json={'choices': [{'message': {'content': 'visible'}}]}))
    provider = get_provider_for_model('local:fob-b:same:model')
    result = await provider.query('local:fob-b:same:model', [{'role': 'user', 'content': 'repair'}], temperature=0.25)
    assert result['content'] == 'visible'
    assert json.loads(route.calls[0].request.content)['model'] == 'same:model'
    assert json.loads(route.calls[0].request.content)['temperature'] == 0.25
    assert 'authorization' not in route.calls[0].request.headers
    with pytest.raises(ValueError):
        await provider.query('local:fob-a:same:model', [])


@pytest.mark.parametrize('model', ['local:missing:qwen', 'local:fob-a', 'local:fob-a:'])
def test_unknown_or_malformed_local_never_falls_back(local_settings, model):
    with pytest.raises(ValueError):
        get_provider_for_model(model)


def test_disabled_endpoint_is_rejected(local_settings):
    local_settings.local_endpoints[0].enabled = False
    with pytest.raises(ValueError):
        get_provider_for_model('local:fob-a:qwen')


@respx.mock
async def test_stream_visible_deltas_usage_and_finish_only(local_settings):
    chunks = [
        {'choices': [{'delta': {'reasoning_content': 'private', 'content': 'inspect '}, 'finish_reason': None}]},
        {'choices': [{'delta': {'content': 'the ground'}, 'finish_reason': 'stop'}]},
        {'choices': [], 'usage': {'prompt_tokens': 5, 'completion_tokens': 3}},
    ]
    body = ''.join(f'data: {json.dumps(chunk)}\n\n' for chunk in chunks) + 'data: [DONE]\n\n'
    route = respx.post('http://127.0.0.1:18081/v1/chat/completions').mock(return_value=httpx.Response(200, text=body))
    events = [e async for e in LocalOpenAIProvider('fob-a').stream_query('local:fob-a:qwen', [])]
    assert [e.delta for e in events if e.type == 'text_delta'] == ['inspect ', 'the ground']
    assert events[-1].type == 'completed'
    assert events[-1].finish_reason == 'stop'
    assert events[-1].usage == {'prompt_tokens': 5, 'completion_tokens': 3}
    assert 'private' not in str(events)
    payload = json.loads(route.calls[0].request.content)
    assert payload['stream'] is True and payload['model'] == 'qwen'


@respx.mock
async def test_stream_http_error_and_incomplete_stream_are_not_success(local_settings):
    route = respx.post('http://127.0.0.1:18081/v1/chat/completions')
    route.mock(return_value=httpx.Response(503, text='unavailable'))
    events = [e async for e in LocalOpenAIProvider('fob-a').stream_query('local:fob-a:qwen', [])]
    assert events[-1].type == 'error'
    route.mock(return_value=httpx.Response(200, text='data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'))
    events = [e async for e in LocalOpenAIProvider('fob-a').stream_query('local:fob-a:qwen', [])]
    assert events[0].delta == 'partial'
    assert events[-1].type == 'error'


@respx.mock
async def test_local_stream_cancellation_closes_transport(local_settings):
    import asyncio

    closed = asyncio.Event()
    waiting = asyncio.Event()

    class BlockingStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
            waiting.set()
            await asyncio.Event().wait()

        async def aclose(self):
            closed.set()

    respx.post('http://127.0.0.1:18081/v1/chat/completions').mock(return_value=httpx.Response(200, stream=BlockingStream()))
    events = []

    async def consume():
        async for event in LocalOpenAIProvider('fob-a').stream_query('local:fob-a:qwen', []):
            events.append(event)

    task = asyncio.create_task(consume())
    await asyncio.wait_for(waiting.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert events[0].delta == 'partial'
    assert closed.is_set()


@pytest.fixture
def local_api(tmp_path, monkeypatch):
    import backend.main as main
    import backend.settings as settings_module
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings_module, 'SETTINGS_FILE', tmp_path / 'settings.json')
    monkeypatch.setattr(settings_module, '_settings_cache', None)
    monkeypatch.setattr(settings_module, '_settings_mtime', None)
    monkeypatch.setattr(main, '_ADMIN_TOKEN', '')
    monkeypatch.setattr(main, 'get_api_key', lambda _: '')
    monkeypatch.setattr(main, 'apply_settings_secret_updates', lambda updates: updates)
    monkeypatch.setattr(main, 'build_settings_response', lambda s: {'local_endpoints': [e.model_dump() for e in s.local_endpoints]})
    with TestClient(main.app, client=('127.0.0.1', 50000)) as client:
        yield client, settings_module


def test_settings_roundtrip_and_invalid_requests(local_api):
    client, settings_module = local_api
    response = client.put('/api/settings', json={'local_endpoints': [endpoint()]})
    assert response.status_code == 200
    assert response.json()['local_endpoints'][0]['id'] == 'fob-a'
    assert json.loads(settings_module.SETTINGS_FILE.read_text())['local_endpoints'][0]['name'] == 'FOB A'
    for payload in [[endpoint(), endpoint()], [endpoint(api_key='secret')], [endpoint(url='ftp://localhost/v1')]]:
        assert client.put('/api/settings', json={'local_endpoints': payload}).status_code == 422
    assert client.put('/api/settings', json={'local_endpoints': []}).json()['local_endpoints'] == []


def test_local_discovery_rejects_non_loopback_before_network(monkeypatch):
    from backend.main import app
    import backend.main as main
    from fastapi.testclient import TestClient
    monkeypatch.setattr(main, '_ADMIN_TOKEN', '')
    with TestClient(app, client=('203.0.113.10', 50000)) as client:
        assert client.get('/api/local-endpoints/models').status_code in (401, 403)


@respx.mock
def test_discovery_isolates_failed_disabled_and_empty_endpoints(local_api):
    client, _ = local_api
    endpoints = [endpoint(), endpoint('fob-b', url='http://127.0.0.1:18082/v1'), endpoint('off', enabled=False)]
    assert client.put('/api/settings', json={'local_endpoints': endpoints}).status_code == 200
    respx.get('http://127.0.0.1:18081/v1/models').mock(return_value=httpx.Response(200, json={'data': [{'id': 'qwen'}]}))
    respx.get('http://127.0.0.1:18082/v1/models').mock(return_value=httpx.Response(503))
    response = client.get('/api/local-endpoints/models')
    assert response.status_code == 200
    assert response.json()['models'][0]['id'] == 'local:fob-a:qwen'
    assert response.json()['errors'][0]['id'] == 'fob-b'
    assert len(response.json()['errors']) == 1


@respx.mock
async def test_transport_timeout_preserves_worker_and_moderator_classification(local_settings):
    from backend.modelmix.orchestrator import multiplex_workers
    from backend.modelmix.moderator import assemble_moderator_input, run_moderator

    respx.post('http://127.0.0.1:18081/v1/chat/completions').mock(side_effect=httpx.ReadTimeout('slow'))
    provider = LocalOpenAIProvider('fob-a')
    events = []

    async def emit(event_type, **payload):
        event = {'type': event_type, **payload}
        events.append(event)
        return event

    events.extend([event async for event in multiplex_workers('repair', 'local:fob-a:qwen', None, lambda _: provider)])
    assert next(e for e in events if e['type'] == 'seat_failed')['reason'] == 'timeout'
    events.clear()
    await run_moderator('local:fob-a:qwen', provider, assemble_moderator_input('repair', {}, {}), emit)
    assert next(e for e in events if e['type'] == 'moderator_failed')['reason'] == 'timeout'


def test_browser_cors_exposes_run_and_session_identity(local_api):
    client, _ = local_api
    response = client.get('/api/local-endpoints/models', headers={'Origin': 'http://127.0.0.1:5173'})
    exposed = response.headers.get('access-control-expose-headers', '').lower()
    assert 'x-modelmix-run-id' in exposed
    assert 'x-modelmix-session-id' in exposed


@respx.mock
async def test_same_endpoint_serializes_full_streams_and_cancellation_releases_waiter(local_settings):
    import asyncio
    started = asyncio.Event()
    active = 0
    peak = 0
    calls = 0

    class Blocking(httpx.AsyncByteStream):
        async def __aiter__(self):
            nonlocal active, peak, calls
            active += 1
            peak = max(peak, active)
            calls += 1
            started.set()
            try:
                yield b'data: {"choices":[{"delta":{"content":"visible"}}]}\n\n'
                await asyncio.Event().wait()
            finally:
                active -= 1

    respx.post('http://127.0.0.1:18081/v1/chat/completions').mock(side_effect=lambda _: httpx.Response(200, stream=Blocking()))
    async def consume():
        return [e async for e in LocalOpenAIProvider('fob-a').stream_query('local:fob-a:qwen', [])]

    first = asyncio.create_task(consume())
    await asyncio.wait_for(started.wait(), 1)
    started.clear()
    waiting = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    assert calls == 1
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    await asyncio.wait_for(started.wait(), 1)
    waiting.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiting
    assert peak == 1
    assert active == 0


@respx.mock
async def test_response_model_mismatch_is_visible_failure_before_content(local_settings):
    body = 'data: {"model":"wrong-model","choices":[{"delta":{"content":"wrong output"}}]}\n\n'
    respx.post('http://127.0.0.1:18081/v1/chat/completions').mock(return_value=httpx.Response(200,text=body))
    events = [e async for e in LocalOpenAIProvider('fob-a').stream_query('local:fob-a:qwen', [])]
    assert len(events) == 1
    assert events[0].type == 'error'
    assert 'model identity mismatch' in events[0].error_message.lower()
    assert 'wrong output' not in str(events)


@respx.mock
async def test_different_local_endpoints_do_not_wait_for_each_other(local_settings):
    import asyncio
    arrived = []
    ready = asyncio.Event()

    class Blocking(httpx.AsyncByteStream):
        async def __aiter__(self):
            arrived.append(1)
            if len(arrived) == 2:
                ready.set()
            await ready.wait()
            yield b'data: [DONE]\n\n'

    for port in [18081, 18082]:
        respx.post(f'http://127.0.0.1:{port}/v1/chat/completions').mock(side_effect=lambda _: httpx.Response(200,stream=Blocking()))
    async def consume(endpoint_id):
        return [e async for e in LocalOpenAIProvider(endpoint_id).stream_query(f'local:{endpoint_id}:qwen', [])]
    results = await asyncio.wait_for(asyncio.gather(consume('fob-a'),consume('fob-b')),1)
    assert all(events[-1].type == 'completed' for events in results)


@respx.mock
async def test_cancel_waiting_local_request_does_not_switch_or_block_active_model(local_settings):
    import asyncio
    ready = asyncio.Event()
    finish = asyncio.Event()
    calls = 0

    class Blocking(httpx.AsyncByteStream):
        async def __aiter__(self):
            ready.set()
            await finish.wait()
            yield b'data: [DONE]\n\n'

    def reply(_):
        nonlocal calls
        calls += 1
        return httpx.Response(200,stream=Blocking())
    respx.post('http://127.0.0.1:18081/v1/chat/completions').mock(side_effect=reply)
    async def consume():
        return [e async for e in LocalOpenAIProvider('fob-a').stream_query('local:fob-a:qwen', [])]
    active = asyncio.create_task(consume())
    await asyncio.wait_for(ready.wait(),1)
    waiting = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    waiting.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiting
    assert calls == 1
    finish.set()
    assert (await active)[-1].type == 'completed'
    assert (await consume())[-1].type == 'completed'


@respx.mock
@pytest.mark.parametrize('streaming', [True, False])
async def test_queued_request_keeps_submitted_endpoint_snapshot(local_settings, streaming):
    import asyncio
    entered = asyncio.Event()
    release = asyncio.Event()

    class Waiting(httpx.AsyncByteStream):
        async def __aiter__(self):
            entered.set()
            await release.wait()
            yield (b'data: [DONE]\n\n' if streaming else b'{"choices":[{"message":{"content":"ok"}}]}')

    old = respx.post('http://127.0.0.1:18081/v1/chat/completions').mock(side_effect=lambda _: httpx.Response(200,stream=Waiting()))
    new = respx.post('http://127.0.0.1:18082/v1/chat/completions').mock(return_value=httpx.Response(200,text='data: [DONE]\n\n'))
    async def consume():
        provider = LocalOpenAIProvider('fob-a')
        if streaming:
            return [e async for e in provider.stream_query('local:fob-a:qwen', [])]
        return await provider.query('local:fob-a:qwen', [])
    active = asyncio.create_task(consume())
    await asyncio.wait_for(entered.wait(),1)
    queued = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    local_settings.local_endpoints[0].url = 'http://127.0.0.1:18082/v1'
    release.set()
    await asyncio.gather(active,queued)
    assert old.call_count == 2
    assert new.call_count == 0

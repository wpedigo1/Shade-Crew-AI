"""Deterministic orchestration tests; scripted models prove flow, not model accuracy."""
import asyncio
import json
from functools import partial

import pytest

from backend.modelmix.verification import run_crew_chief, PublicSearchEvidence
from backend.modelmix.registry import RunRegistry
from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.tests.test_modelmix_moderator import StreamingProvider


class Chief(StreamingProvider):
    def __init__(self, plan, verdicts):
        super().__init__()
        self.plan = plan
        self.verdicts = verdicts
        self.calls = []

    async def stream_query(self, model_id, messages, **kwargs):
        from backend.providers.base import ProviderStreamEvent
        if not messages[-1]['content'].startswith('Evidence ledger:'):
            self.calls.append(messages)
            data = self.plan if len(self.calls) == 1 else self.verdicts
            yield ProviderStreamEvent(type='text_delta', delta=json.dumps(data))
            yield ProviderStreamEvent(type='completed', finish_reason='stop', usage={'total_tokens': 12})
            return
        self.messages.append(messages)
        evidence = json.loads(messages[-1]['content'].split('Evidence ledger:\n')[1])
        status = evidence[0]['result'] if evidence else 'not necessary to verify'
        supported = evidence[0].get('quote', '') if evidence else ''
        yield ProviderStreamEvent(type='text_delta', delta=f'Based on evidence: {status}; {supported}')
        yield ProviderStreamEvent(type='completed', finish_reason='stop')


class Evidence:
    def __init__(self, fail=False, gate=None):
        self.queries = []
        self.fail = fail
        self.gate = gate
        self.cancelled = False

    async def search(self, query):
        self.queries.append(query)
        try:
            if self.gate:
                await self.gate.wait()
            if self.fail:
                raise RuntimeError('offline')
            return [{'source_id': 's1', 'title': 'Reference', 'url': 'https://example.org/spec',
                     'excerpt': 'The reference specifies 12 volts.', 'kind': 'search_snippet'}]
        except asyncio.CancelledError:
            self.cancelled = True
            raise


def plan(needed=True):
    return {'claims': [{'claim': 'Supply is 24 volts', 'query': 'supply voltage specification',
                        'needs_verification': needed}]}


def verdict(result='contradicted', quote='12 volts'):
    return {'verdicts': [{'claim_id': 'c1', 'result': result, 'summary': 'Reference specifies 12 V.',
                          'source_id': 's1', 'quote': quote}]}


async def start(tmp_path, chief, adapter, a='24 volts', b='48 volts', **kwargs):
    store = AtomicJsonModelMixPersistence(tmp_path)
    registry = RunRegistry(persistence=store, moderator_runner=partial(run_crew_chief, adapter=adapter), **kwargs)
    providers = {'a': StreamingProvider((a,)), 'b': StreamingProvider((b,)), 'm': chief}
    run = await registry.start('Check supply', 'a', 'b', providers.__getitem__, 'm')
    return registry, run, providers


@pytest.mark.parametrize('b', ['48 volts', '24 volts'])
async def test_conflict_and_false_agreement_use_evidence_and_can_reject_both(tmp_path, b):
    review = {'claims': [plan()['claims'][0], {**plan()['claims'][0], 'claim': f'Grease Monkey says {b}'}]}
    findings = {'verdicts': [verdict()['verdicts'][0], {**verdict()['verdicts'][0], 'claim_id': 'c2'}]}
    chief, adapter = Chief(review, findings), Evidence()
    registry, run, providers = await start(tmp_path, chief, adapter, b=b)
    await run.task
    assert run.status == 'completed'
    assert adapter.queries == ['supply voltage specification'] * 2
    assert '24 volts' in chief.calls[0][-2]['content'] and b in chief.calls[0][-2]['content']
    assert providers['a'].messages == [[{'role': 'user', 'content': 'Check supply'}]]
    assert providers['b'].messages == [[{'role': 'user', 'content': 'Check supply'}]]
    assert 'Based on evidence: contradicted' in str(run._events)
    saved = await AtomicJsonModelMixPersistence(tmp_path).load_session(run.session_id)
    message = next(m for m in saved['session']['messages'] if m['seat'] == 'moderator')
    assert len(message['evidence']) == 2
    assert all(item['result'] == 'contradicted' for item in message['evidence'])
    assert '12 volts' in str(run._events)
    evidence = message['evidence'][0]
    assert evidence['result'] == 'contradicted'
    assert evidence['sources'][0]['url'] == 'https://example.org/spec'
    assert evidence['quote'] == '12 volts'
    replay = await run.events_after(0)
    assert [e['seq'] for e in replay] == list(range(1, len(replay) + 1))
    assert any(e['type'] == 'moderator_evidence' for e in replay)


@pytest.mark.parametrize('result,quote,fail', [('unresolved', '', False), ('verified', 'invented quote', False), ('verified', '12 volts', True)])
async def test_failure_inconclusive_or_unbound_quote_stays_unresolved(tmp_path, result, quote, fail):
    chief = Chief(plan(), verdict(result, quote))
    _, run, _ = await start(tmp_path, chief, Evidence(fail=fail))
    await run.task
    evidence = [e['evidence'] for e in run._events if e['type'] == 'moderator_evidence'][-1]
    assert evidence['result'] == 'unresolved'
    assert 'Based on evidence: unresolved' in str(run._events)
    if fail:
        assert evidence['error'] == 'Research failed'


async def test_no_verification_needed_skips_search_and_assessment(tmp_path):
    chief, adapter = Chief(plan(False), {}), Evidence()
    _, run, _ = await start(tmp_path, chief, adapter)
    await run.task
    assert adapter.queries == []
    assert len(chief.calls) == 1
    assert 'not necessary to verify' in str(run._events)


async def test_cancel_during_verification_retains_unresolved_claim(tmp_path):
    adapter = Evidence(gate=asyncio.Event())
    registry, run, _ = await start(tmp_path, Chief(plan(), verdict()), adapter)
    while not adapter.queries:
        await asyncio.sleep(0)
    await registry.cancel(run.run_id)
    await run.task
    assert adapter.cancelled
    assert run.status == 'cancelled'
    saved = await registry.persistence.load_session(run.session_id)
    msg = next(m for m in saved['session']['messages'] if m['seat'] == 'moderator')
    assert msg['evidence'][0]['result'] == 'unresolved'
    assert not any(e['type'] == 'moderator_completed' for e in run._events)


async def test_real_adapter_returns_structured_sources(monkeypatch):
    class Search:
        def __init__(self, **kwargs): pass
        def text(self, query, **kwargs):
            assert kwargs['max_results'] == 3
            return [{'title': 'Source', 'href': 'https://example.org', 'body': 'Actual excerpt'}]
    monkeypatch.setattr('backend.modelmix.verification.DDGS', Search)
    assert (await PublicSearchEvidence().search('voltage'))[0]['excerpt'] == 'Actual excerpt'

@pytest.mark.parametrize('result', ['verified', 'contradicted'])
async def test_supported_verdict_requires_retrieved_quote(tmp_path, result):
    _, run, _ = await start(tmp_path, Chief(plan(), verdict(result)), Evidence())
    await run.task
    last = [e['evidence'] for e in run._events if e['type'] == 'moderator_evidence'][-1]
    assert last['result'] == result
    assert last['source_id'] == 's1'


@pytest.mark.parametrize('review', [{}, {'claims': 'not a list'}, {'claims': [plan()['claims'][0]] * 4}])
async def test_invalid_or_over_budget_plan_fails_closed_without_search(tmp_path, review):
    adapter = Evidence()
    _, run, _ = await start(tmp_path, Chief(review, {}), adapter)
    await run.task
    assert adapter.queries == []
    assert 'Claim review failed' in str(run._events)
    assert run.status == 'completed'


async def test_three_sequential_tools_maximum(tmp_path):
    review = {'claims': plan()['claims'] * 3}
    adapter = Evidence()
    chief = Chief(review, {})
    _, run, _ = await start(tmp_path, chief, adapter)
    await run.task
    assert len(adapter.queries) == 3
    assert len(chief.calls) == 2
    assert all(e['evidence']['result'] == 'unresolved' for e in run._events if e['type'] == 'moderator_evidence')


async def test_tool_timeout_is_unresolved_and_final_can_continue(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.modelmix.verification.TOOL_TIMEOUT', 0.01)
    _, run, _ = await start(tmp_path, Chief(plan(), {}), Evidence(gate=asyncio.Event()))
    await run.task
    assert run.status == 'completed'
    assert 'Research failed' in str(run._events)
    assert 'Based on evidence: unresolved' in str(run._events)


async def test_total_deadline_covers_verification_and_retains_unresolved(tmp_path):
    _, run, _ = await start(tmp_path, Chief(plan(), {}), Evidence(gate=asyncio.Event()), seat_timeout=0.03)
    await run.task
    assert run.status == 'failed'
    assert any(e['type'] == 'moderator_failed' and e['reason'] == 'timeout' for e in run._events)
    assert 'Verification interrupted' in str(run._events)


async def test_empty_sources_are_not_evidence(tmp_path):
    class Empty(Evidence):
        async def search(self, query): return []
    chief = Chief(plan(), verdict('verified'))
    _, run, _ = await start(tmp_path, chief, Empty())
    await run.task
    assert len(chief.calls) == 1
    assert 'No usable sources' in str(run._events)


async def test_unknown_source_or_duplicate_verdict_cannot_verify(tmp_path):
    assessment = verdict('verified')
    assessment['verdicts'][0]['source_id'] = 'invented'
    _, run, _ = await start(tmp_path, Chief(plan(), assessment), Evidence())
    await run.task
    assert [e['evidence'] for e in run._events if e['type'] == 'moderator_evidence'][-1]['result'] == 'unresolved'

async def test_additional_review_cost_is_retained_separately(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.modelmix.verification.compute_openrouter_cost_usd', lambda model, usage: 0.2)
    registry, run, _ = await start(tmp_path, Chief(plan(), verdict()), Evidence())
    await run.task
    saved = await registry.persistence.load_session(run.session_id)
    chief = next(m for m in saved['session']['messages'] if m['seat'] == 'moderator')
    assert chief['verification_cost_usd'] == 0.4
    assert len(chief['verification_usage']) == 2

@pytest.mark.parametrize('streaming', [True, False])
@pytest.mark.parametrize('finish_reason', ['length', 'content_filter'])
async def test_rejected_structured_completion_retains_reported_usage(streaming, finish_reason):
    from backend.modelmix.verification import _json_call
    from backend.providers.base import ProviderStreamEvent
    class Incomplete(Chief):
        @property
        def supports_streaming(self): return streaming
        async def stream_query(self, *args, **kwargs):
            yield ProviderStreamEvent(type='text_delta', delta='{}')
            yield ProviderStreamEvent(type='completed', finish_reason=finish_reason, usage={'total_tokens': 42})
        async def query(self, *args, **kwargs):
            return {'content': '{}', 'finish_reason': finish_reason, 'usage': {'total_tokens': 42}}
    events = []
    async def emit(kind, **payload): events.append({'type': kind, **payload})
    with pytest.raises(ValueError):
        await _json_call('m', Incomplete({}, {}), [], emit, None)
    assert events[0]['type'] == 'moderator_verification_usage'
    assert events[0]['usage']['total_tokens'] == 42

async def test_oauth_shaped_completed_status_can_review_and_verify(tmp_path):
    from backend.providers.base import ProviderStreamEvent
    class OAuthChief(Chief):
        async def stream_query(self, *args, **kwargs):
            async for event in super().stream_query(*args, **kwargs):
                if event.type == 'completed':
                    event = ProviderStreamEvent(type='completed', finish_reason='completed', usage=event.usage)
                yield event
    chief, adapter = OAuthChief(plan(), verdict()), Evidence()
    _, run, _ = await start(tmp_path, chief, adapter)
    await run.task
    assert adapter.queries
    assert [e['evidence'] for e in run._events if e['type'] == 'moderator_evidence'][-1]['result'] == 'contradicted'

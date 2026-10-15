"""Case research integration uses scripted providers, real registry/persistence."""
import asyncio
import json

import pytest

from backend.modelmix.budgets import ResearchBudget
from backend.modelmix.cases import CasePersistence
from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.modelmix.research import run_research_seat
from backend.providers.base import LLMProvider, ProviderStreamEvent

BUDGET = ResearchBudget(seconds=5, output_chars=20_000, reported_tokens=30_000, context_chars=80_000, emergency_actions=128)


class Scripted(LLMProvider):
    def __init__(self, actions, final='Visible final answer'):
        self.actions = list(actions)
        self.messages = []
        self.final = final

    @property
    def supports_streaming(self): return True

    async def stream_query(self, model_id, messages, **kwargs):
        self.messages.append(messages)
        control = 'RESEARCH_CONTROL' in messages[-1]['content']
        content = json.dumps(self.actions.pop(0)) if control else self.final
        yield ProviderStreamEvent(type='text_delta', delta=content)
        yield ProviderStreamEvent(type='completed', usage={'total_tokens': 10}, finish_reason='stop')

    async def query(self, *args, **kwargs): raise AssertionError('stream path required')
    async def get_models(self): return []
    async def validate_key(self, key): return {'success': True}


class Search:
    def __init__(self, gate=None):
        self.queries = []
        self.gate = gate
        self.cancelled = False

    async def search(self, query):
        self.queries.append(query)
        try:
            if self.gate:
                await self.gate.wait()
            return [{'source_id': 's1', 'title': 'Specification', 'url': 'https://example.org/spec',
                     'excerpt': 'Supply is 12 volts.', 'kind': 'search_snippet'}]
        except asyncio.CancelledError:
            self.cancelled = True
            raise


def finish(**kwargs): return {'action': 'finish', **kwargs}
def search(query='supply spec'): return {'action': 'search', 'query': query}


async def execute(tmp_path, provider, seat='worker_a', adapter=None, budget=BUDGET, peer_work=None, peer_answers=None):
    repo = CasePersistence(tmp_path / 'cases', legacy=AtomicJsonModelMixPersistence(tmp_path / 'legacy'))
    doc = await repo.create_case('Test job')
    snapshot = {**doc['case'], 'question': 'Check supply'}
    events = []
    async def emit(kind, **data):
        event = {'type': kind, **data}
        events.append(event)
        return event
    await run_research_seat(seat, 'local:fob:model', provider, [{'role': 'user', 'content': 'Check supply'}], emit,
                            snapshot=snapshot, resources=repo, budget=budget, adapter=adapter or Search(), peer_work=peer_work or {}, peer_answers=peer_answers)
    return events, repo, doc


@pytest.mark.parametrize('seat', ['worker_a', 'worker_b'])
async def test_mechanics_can_research_beyond_three_searches(tmp_path, seat):
    adapter = Search()
    provider = Scripted([search(f'query{i}') for i in range(5)] + [finish()])
    events, _, _ = await execute(tmp_path, provider, seat, adapter)
    assert len(adapter.queries) == 5
    tools = [e for e in events if e['type'] == 'tool_completed']
    assert len(tools) == 5
    assert all(e['seat_id'] == seat for e in tools)
    assert tools[0]['tool']['result'][0]['source_id'].startswith(seat + ':')
    assert any(e['type'] == 'seat_completed' for e in events)


async def test_chief_salvages_source_rejects_interpretation_and_rechecks(tmp_path):
    work = {'worker_a': [{'tool_id': 't1', 'name': 'search', 'status': 'completed', 'arguments': {'query': 'spec'},
                         'result': [{'source_id': 'worker_a:t1:s1', 'title': 'Spec', 'url': 'https://example.org',
                                     'excerpt': 'Supply is 12 volts.', 'kind': 'search_snippet'}]}], 'worker_b': []}
    finding = {'claim': 'Supply is 24 volts', 'result': 'contradicted', 'source_id': 'worker_a:t1:s1',
               'quote': '12 volts', 'summary': 'Useful source contradicts the mechanic interpretation'}
    adapter = Search()
    provider = Scripted([{'action': 'work.read', 'seat': 'worker_a', 'offset': 0}, search('independent source check'), finish(findings=[finding])])
    events, _, _ = await execute(tmp_path, provider, 'moderator', adapter, peer_work=work)
    assert adapter.queries == ['independent source check']
    ledger = [e['evidence'] for e in events if e['type'] == 'moderator_evidence']
    assert ledger[-1]['result'] == 'contradicted'
    assert 'worker_a:t1:s1' in json.dumps(provider.messages[-1])
    assert any(e['type'] == 'moderator_completed' for e in events)


async def test_worker_cannot_read_peer_work(tmp_path):
    provider = Scripted([{'action': 'work.read', 'seat': 'worker_b'}, finish()])
    events, _, _ = await execute(tmp_path, provider, peer_work={'worker_b': [{'secret': 'peer answer'}]})
    assert 'peer answer' not in json.dumps(provider.messages)
    assert [e['tool'] for e in events if e['type'] == 'tool_completed'][0]['status'] == 'failed'


async def test_cancel_during_research_keeps_pending_and_interrupted_tool(tmp_path):
    adapter = Search(asyncio.Event())
    provider = Scripted([search(), finish()])
    events = []
    async def emit(kind, **data): events.append({'type': kind, **data})
    task = asyncio.create_task(run_research_seat('worker_a', 'a', provider, [{'role': 'user', 'content': 'check'}], emit,
                                               snapshot={}, resources=None, budget=BUDGET, adapter=adapter))
    while not adapter.queries:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert adapter.cancelled
    assert events[-1]['type'] == 'tool_completed'
    assert events[-1]['tool']['status'] == 'cancelled'


async def test_output_budget_leaves_partial_honest_state(tmp_path):
    budget = ResearchBudget(seconds=5, output_chars=100, reported_tokens=3000, context_chars=8000, emergency_actions=128)
    events, _, _ = await execute(tmp_path, Scripted([search('x' * 200)]), budget=budget)
    assert any(e['type'] == 'research_limited' for e in events)
    assert events[-1]['type'] == 'seat_failed'
    assert events[-1]['reason'] == 'resource_exhausted'

async def test_case_run_records_both_workers_and_chief_can_promote_only_supported_facts(tmp_path):
    from backend.modelmix.registry import RunRegistry
    repo = CasePersistence(tmp_path / 'cases', legacy=AtomicJsonModelMixPersistence(tmp_path / 'legacy'))
    cid = (await repo.create_case('Supply issue'))['case']['case_id']
    good = {'claim': 'Supply is 12 volts', 'result': 'verified', 'source_id': 'worker_a:t1:s1',
            'quote': '12 volts', 'summary': 'Retrieved source supports 12 volts'}
    providers = {'a': Scripted([search(), finish()], final='Wrong interpretation: 24 volts'),
                 'b': Scripted([search(), finish()], final='Wrong interpretation: 48 volts'),
                 'm': Scripted([{'action': 'work.read', 'seat': 'worker_a'}, search('independent voltage source'),
                                finish(findings=[good], promotions=[{'subject': 'Supply', 'value': '12', 'unit': 'V',
                                    'status': 'crew_chief_accepted', 'source_id': 'worker_a:t1:s1', 'quote': '12 volts',
                                    'finding_claim': 'Supply is 12 volts'}])], final='Both interpretations are wrong; source supports 12 volts')}
    registry = RunRegistry(persistence=repo, research_adapter=Search())
    run = await registry.start('Check voltage', 'a', 'b', providers.__getitem__, 'm', cid)
    await run.task
    assert run.status == 'completed'
    doc = await repo.load_session(cid)
    messages = {m['seat']: m for m in doc['session']['messages'] if m['role'] == 'assistant'}
    assert messages['worker_a']['research'][0]['result'][0]['excerpt'] == 'Supply is 12 volts.'
    assert messages['worker_b']['research'][0]['name'] == 'search'
    chief_input = json.dumps(providers['m'].messages)
    assert 'Wrong interpretation: 24 volts' in chief_input and 'Wrong interpretation: 48 volts' in chief_input
    assert 'worker_a:t1:s1' in chief_input and 'worker_b:t1:s1' in chief_input
    for seat in ['a', 'b']:
        text = json.dumps(providers[seat].messages)
        assert 'Wrong interpretation' not in text and 'mechanic_work' not in text
    assert doc['case']['facts'] == []  # never promote automatically
    promoted = await repo.accept_promotion(cid, run.run_id, 'p1')
    assert promoted['case']['facts'][0]['value'] == '12'
    assert promoted['case']['facts'][0]['status'] == 'crew_chief_accepted'
    assert promoted['case']['facts'][0]['provenance']['run_id'] == run.run_id
    assert len((await repo.accept_promotion(cid, run.run_id, 'p1'))['case']['facts']) == 1
    reopened = CasePersistence(tmp_path / 'cases', legacy=repo.legacy)
    restored = await RunRegistry(persistence=reopened).restore_persisted(run.run_id)
    assert any(e['type'] == 'tool_completed' for e in await restored.events_after(0))
    assert (await reopened.load_session(cid))['session']['runs'][0]['case_snapshot'] == doc['session']['runs'][0]['case_snapshot']


async def test_case_cancellation_persists_interrupted_worker_tools_before_terminal(tmp_path):
    from backend.modelmix.registry import RunRegistry
    repo = CasePersistence(tmp_path / 'cases', legacy=AtomicJsonModelMixPersistence(tmp_path / 'legacy'))
    cid = (await repo.create_case('Cancel test'))['case']['case_id']
    adapter = Search(asyncio.Event())
    providers = {s: Scripted([search(), finish()]) for s in ['a', 'b', 'm']}
    registry = RunRegistry(persistence=repo, research_adapter=adapter)
    run = await registry.start('inspect', 'a', 'b', providers.__getitem__, 'm', cid)
    while len(adapter.queries) < 2:
        await asyncio.sleep(0)
    await registry.cancel(run.run_id)
    await run.task
    saved = await repo.load_session(cid)
    assert run.status == 'cancelled'
    workers = [m for m in saved['session']['messages'] if m['seat'] in {'worker_a', 'worker_b'}]
    assert all(m['research'][0]['status'] == 'cancelled' for m in workers)
    events = saved['session']['runs'][0]['events']
    assert events[-1]['type'] == 'run_cancelled'
    assert sum(e['type'] == 'tool_completed' and e['tool']['status'] == 'cancelled' for e in events) == 2


async def test_reported_token_budget_and_missing_usage_do_not_fake_totals(tmp_path):
    budget = ResearchBudget(seconds=5, output_chars=1000, reported_tokens=5, context_chars=8000, emergency_actions=128)
    events, _, _ = await execute(tmp_path, Scripted([finish()]), budget=budget)
    assert [e for e in events if e['type'] == 'research_usage'][0]['usage']['total_tokens'] == 10
    assert events[-1]['type'] == 'seat_failed'
    assert not any(e['type'] == 'seat_completed' for e in events)


async def test_tool_timeout_leaves_unresolved_partial_work(tmp_path):
    budget = ResearchBudget(seconds=0.1, output_chars=2000, reported_tokens=3000, context_chars=8000, emergency_actions=128, tool_seconds=0.01)
    events, _, _ = await execute(tmp_path, Scripted([search(), finish()]), adapter=Search(asyncio.Event()), budget=budget)
    tool = [e['tool'] for e in events if e['type'] == 'tool_completed'][0]
    assert tool['status'] == 'timeout'
    assert 'unresolved' in tool['error']
    # Tool failure is visible to the final model, never a verified finding.
    assert not any(e.get('evidence', {}).get('result') == 'verified' for e in events)


def test_default_budgets_broader_for_chief_and_configurable(monkeypatch):
    from backend.modelmix.budgets import case_budgets
    config = case_budgets()
    assert config['chief']['seconds'] > config['mechanic']['seconds']
    assert config['chief']['output_chars'] > config['mechanic']['output_chars']
    assert config['mechanic']['emergency_actions'] >= 100
    monkeypatch.setenv('SHADE_CREW_MECHANIC_SECONDS', '321')
    assert case_budgets()['mechanic']['seconds'] == 321
    monkeypatch.setenv('SHADE_CREW_CHIEF_SECONDS', 'nan')
    with pytest.raises(ValueError):
        case_budgets()


@pytest.mark.parametrize('status,allowed', [('verified', False), ('measured', False), ('crew_chief_accepted', False), ('unresolved', True), ('disputed', True), ('hypothesis', True)])
async def test_unresolved_information_cannot_be_laundered_into_fact(tmp_path, status, allowed):
    from backend.modelmix.registry import RunRegistry
    repo = CasePersistence(tmp_path / 'cases', legacy=AtomicJsonModelMixPersistence(tmp_path / 'legacy'))
    cid = (await repo.create_case('Uncertain job'))['case']['case_id']
    proposal = {'subject': 'Starter', 'value': 'bad', 'status': status}
    providers = {'a': Scripted([finish()]), 'b': Scripted([finish()]), 'm': Scripted([finish(promotions=[proposal])])}
    registry = RunRegistry(persistence=repo, research_adapter=Search())
    run = await registry.start('Unknown cause', 'a', 'b', providers.__getitem__, 'm', cid)
    await run.task
    assert (await repo.load_session(cid))['case']['facts'] == []
    if allowed:
        saved = await repo.accept_promotion(cid, run.run_id, 'p1')
        assert saved['case']['facts'][0]['status'] == status
    else:
        with pytest.raises(ValueError):
            await repo.accept_promotion(cid, run.run_id, 'p1')
        assert (await repo.load_session(cid))['case']['facts'] == []


async def test_accepted_measurement_requires_exact_frozen_measurement(tmp_path):
    from backend.modelmix.registry import RunRegistry
    repo = CasePersistence(tmp_path / 'cases', legacy=AtomicJsonModelMixPersistence(tmp_path / 'legacy'))
    cid = (await repo.create_case('Measured job'))['case']['case_id']
    doc = await repo.add_record(cid, {'subject': 'Battery', 'value': '12.6', 'unit': 'V', 'status': 'measured',
                                     'category': 'measurements', 'provenance': {'kind': 'user_measurement', 'reference': 'At battery posts'}})
    fact_id = doc['case']['measurements'][0]['fact_id']
    proposal = {'subject': 'Battery', 'value': '12.6', 'unit': 'V', 'status': 'measured', 'supporting_fact_ids': [fact_id], 'category': 'measurements'}
    providers = {'a': Scripted([finish()]), 'b': Scripted([finish()]), 'm': Scripted([finish(promotions=[proposal])])}
    run = await RunRegistry(persistence=repo, research_adapter=Search()).start('Retain reading', 'a', 'b', providers.__getitem__, 'm', cid)
    await run.task
    accepted = await repo.accept_promotion(cid, run.run_id, 'p1')
    assert accepted['case']['measurements'][-1]['provenance']['kind'] == 'user_measurement'
    assert accepted['case']['measurements'][-1]['provenance']['supporting_fact_ids'] == [fact_id]


async def test_promotion_cannot_borrow_unverified_passage_from_same_source(tmp_path):
    from backend.modelmix.registry import RunRegistry
    repo = CasePersistence(tmp_path / 'cases', legacy=AtomicJsonModelMixPersistence(tmp_path / 'legacy'))
    cid = (await repo.create_case('Binding test'))['case']['case_id']
    class MultiFact(Search):
        async def search(self, query):
            return [{'source_id': 's1', 'title': 'Mixed spec', 'url': 'https://example.org', 'excerpt': 'Supply is 12 volts. Oil pressure is 99 psi.', 'kind': 'search_snippet'}]
    finding = {'claim': 'Supply is 12 volts', 'result': 'verified', 'source_id': 'worker_a:t1:s1', 'quote': '12 volts', 'summary': 'Voltage checked'}
    candidate = {'subject': 'Oil pressure', 'value': '99', 'status': 'crew_chief_accepted', 'source_id': 'worker_a:t1:s1', 'quote': '99 psi', 'finding_claim': 'Supply is 12 volts'}
    providers = {'a': Scripted([search(), finish()]), 'b': Scripted([finish()]), 'm': Scripted([finish(findings=[finding], promotions=[candidate])])}
    run = await RunRegistry(persistence=repo, research_adapter=MultiFact()).start('Check voltage', 'a', 'b', providers.__getitem__, 'm', cid)
    await run.task
    with pytest.raises(ValueError):
        await repo.accept_promotion(cid, run.run_id, 'p1')


async def test_work_reads_are_nonrecursive_and_tool_results_bounded(tmp_path):
    provider = Scripted([{'action': 'work.read', 'offset': max(0, n - 3)} for n in range(16)] + [finish()])
    events, _, _ = await execute(tmp_path, provider)
    results = [e['tool']['result'] for e in events if e['type'] == 'tool_completed']
    assert max(len(json.dumps(result)) for result in results) < 16_000
    assert len(json.dumps(events)) < 100_000


async def test_proposals_retain_only_visible_decision_fields(tmp_path):
    provider = Scripted([finish(promotions=[{'subject': 'Cause', 'value': 'unknown', 'status': 'unresolved', 'reasoning': 'PRIVATE_SENTINEL'}])])
    events, _, _ = await execute(tmp_path, provider, seat='moderator')
    assert 'PRIVATE_SENTINEL' not in json.dumps(events)
    assert [e['candidate'] for e in events if e['type'] == 'moderator_promotion_proposed'][0]['status'] == 'unresolved'


async def test_chief_can_page_complete_worker_answer_without_treating_it_as_proof(tmp_path):
    answer = 'A' * 4000 + 'B' * 4000 + 'End'
    provider = Scripted([{'action': 'work.read', 'seat': 'worker_a', 'section': 'answer', 'offset': 0},
                         {'action': 'work.read', 'seat': 'worker_a', 'section': 'answer', 'offset': 4000},
                         {'action': 'work.read', 'seat': 'worker_a', 'section': 'answer', 'offset': 8000}, finish()])
    events, _, _ = await execute(tmp_path, provider, 'moderator', peer_answers={'worker_a': answer})
    reads = [e['tool']['result'] for e in events if e['type'] == 'tool_completed']
    assert ''.join(r['answer_excerpt'] for r in reads) == answer
    assert all(r['kind'] == 'mechanic_opinion' and 'source_id' not in r for r in reads)


async def test_case_run_deadline_settles_pending_work_and_retains_snapshot(tmp_path):
    from backend.modelmix.registry import RunRegistry
    repo = CasePersistence(tmp_path / 'cases', legacy=AtomicJsonModelMixPersistence(tmp_path / 'legacy'))
    cid = (await repo.create_case('Whole-run timeout'))['case']['case_id']
    providers = {'a': Scripted([search(), finish()])}
    registry = RunRegistry(persistence=repo, research_adapter=Search(asyncio.Event()), run_timeout=0.03)
    run = await registry.start('Wait for research', 'a', None, providers.__getitem__, session_id=cid)
    await run.task
    doc = await repo.load_session(cid)
    assert doc['session']['runs'][0]['execution_budgets']['run_seconds'] == 0.03
    assert doc['session']['runs'][0]['case_snapshot']['question'] == 'Wait for research'
    assert run.status == 'failed'
    assert doc['session']['runs'][0]['events'][-1]['reason'] == 'timeout'
    assert next(m for m in doc['session']['messages'] if m['seat'] == 'worker_a')['research'][0]['status'] == 'timeout'

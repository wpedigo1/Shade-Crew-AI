"""Case durability, provenance and immutable snapshots without model inference."""

import pytest

from backend.modelmix.cases import CasePersistence
from backend.modelmix.persistence import AtomicJsonModelMixPersistence, PersistenceError


def store(tmp_path):
    return CasePersistence(tmp_path / 'cases', legacy=AtomicJsonModelMixPersistence(tmp_path / 'sessions'))


def run(run_id='r1'):
    return {'run_id': run_id, 'prompt': 'No crank', 'models': {'worker_a': 'a', 'worker_b': 'b', 'moderator': 'm'},
            'status': 'created', 'latest_seq': 0, 'events': []}


async def test_create_reopen_and_named_folder_state(tmp_path):
    repo = store(tmp_path)
    doc = await repo.create_case('Truck no crank')
    cid = doc['case']['case_id']
    assert (tmp_path / 'cases' / cid / 'case.json').exists()
    reopened = await store(tmp_path).load_session(cid)
    assert reopened['case']['name'] == 'Truck no crank'
    assert (await repo.list_cases())[0]['case_id'] == cid
    await repo.update_case(cid, name='Truck starting diagnosis', machine={'engine': 'unknown'})
    assert (await store(tmp_path).load_session(cid))['case']['machine'] == {'engine': 'unknown'}


async def test_fact_provenance_and_two_runs_have_frozen_context(tmp_path):
    repo = store(tmp_path)
    cid = (await repo.create_case('Truck'))['case']['case_id']
    first = await repo.add_record(cid, {'category': 'measurements', 'subject': 'Battery voltage', 'value': '12.6', 'unit': 'V',
                                      'status': 'measured', 'provenance': {'kind': 'user_measurement', 'reference': 'Meter at battery posts'}})
    await repo.create_run(cid, run())
    snapshot = (await repo.load_session(cid))['session']['runs'][0]['case_snapshot']
    await repo.add_record(cid, {'subject': 'Starter failure', 'value': 'possible', 'status': 'hypothesis',
                               'provenance': {'kind': 'user', 'reference': 'Possible cause'}})
    await repo.create_run(cid, run('r2'))
    doc = await store(tmp_path).load_session(cid)
    assert doc['session']['runs'][0]['case_snapshot'] == snapshot
    assert len(doc['session']['runs']) == 2
    assert snapshot['measurements'][0]['provenance']['kind'] == 'user_measurement'
    assert snapshot['revision'] == first['case']['revision']
    assert not snapshot['facts']
    assert doc['session']['runs'][1]['case_snapshot']['facts'][0]['status'] == 'hypothesis'


async def test_invalid_measured_or_verified_provenance_rejected(tmp_path):
    repo = store(tmp_path)
    cid = (await repo.create_case('Job'))['case']['case_id']
    for status in ['verified', 'measured']:
        with pytest.raises((ValueError, PersistenceError)):
            await repo.add_record(cid, {'subject': 'guess', 'value': '12', 'status': status,
                                       'provenance': {'kind': 'model', 'reference': 'Guess'}})


async def test_legacy_import_copies_without_modifying_original(tmp_path):
    repo = store(tmp_path)
    await repo.legacy.create_session('legacy')
    original_path = tmp_path / 'sessions' / 'legacy.json'
    original = original_path.read_bytes()
    doc = await repo.import_legacy('legacy', 'Imported job')
    assert doc['case']['imported_from'] == 'legacy'
    assert original_path.read_bytes() == original
    assert (await repo.load_session('legacy'))['session']['session_id'] == 'legacy'
    assert (await repo.import_legacy('legacy', 'Again'))['case']['case_id'] == doc['case']['case_id']
    with pytest.raises(PersistenceError):
        await repo.create_run('legacy', run())


async def test_attachment_content_addressed_and_snapshot_scoped(tmp_path):
    repo = store(tmp_path)
    one = (await repo.create_case('One'))['case']['case_id']
    two = (await repo.create_case('Two'))['case']['case_id']
    doc = await repo.add_attachment(one, '../notes.txt', b'Battery measured 12.6 V', 'text/plain')
    await repo.add_attachment(two, 'same.txt', b'Battery measured 12.6 V', 'text/plain')
    assert len(list((tmp_path / 'objects').iterdir())) == 1
    ref = doc['case']['attachments'][0]
    assert ref['filename'] == 'notes.txt'
    assert (await repo.read_attachment(ref, 0))['excerpt'] == 'Battery measured 12.6 V'
    with pytest.raises(PersistenceError):
        await repo.read_attachment({**ref, 'sha256': '../../secret'}, 0)


async def test_case_id_cannot_escape_root(tmp_path):
    repo = store(tmp_path)
    with pytest.raises(PersistenceError):
        await repo.load_session('../outside')


async def test_restart_recovery_marks_pending_research_interrupted(tmp_path):
    from backend.modelmix.registry import RunRegistry
    repo = store(tmp_path)
    cid = (await repo.create_case('Interrupted job'))['case']['case_id']
    await repo.create_run(cid, run())
    await repo.append_event(cid, 'r1', {'run_id': 'r1', 'seq': 1, 'ts': 1, 'type': 'tool_started', 'seat_id': 'worker_a', 'model': 'a',
                                      'tool': {'tool_id': 't1', 'name': 'search', 'arguments': {'query': 'spec'}, 'status': 'running'}}, 'active')
    restored = await RunRegistry(persistence=store(tmp_path)).restore_persisted('r1')
    assert restored.status == 'failed'
    doc = await repo.load_session(cid)
    worker = next(m for m in doc['session']['messages'] if m['seat'] == 'worker_a')
    assert worker['research'][0]['status'] == 'interrupted'
    assert doc['session']['runs'][0]['events'][-1]['reason'] == 'backend_restart'


async def test_attachment_failure_never_publishes_incomplete_hash_object(tmp_path, monkeypatch):
    import hashlib
    repo = store(tmp_path)
    cid = (await repo.create_case('Atomic attachment'))['case']['case_id']
    content = b'Important measured information'
    digest = hashlib.sha256(content).hexdigest()
    def fail_sync(fd):
        raise OSError('simulated storage failure')
    monkeypatch.setattr('backend.modelmix.cases.os.fsync', fail_sync)
    with pytest.raises(OSError):
        await repo.add_attachment(cid, 'notes.txt', content, 'text/plain')
    assert not (tmp_path / 'objects' / digest).exists()
    assert (await repo.load_session(cid))['case']['attachments'] == []

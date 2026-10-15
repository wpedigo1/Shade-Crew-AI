"""Named local Cases using the existing atomic JSON session boundary.

One Case document is the sole owner of metadata, runs, snapshots and events.
Legacy session files are readable but never modified by this implementation.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import time
import tempfile
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal

from .persistence import AtomicJsonModelMixPersistence, PersistenceError

STATUSES = Literal['user_reported', 'observed', 'measured', 'verified', 'crew_chief_accepted',
                   'disputed', 'unresolved', 'hypothesis', 'rejected']
CATEGORIES = ('facts', 'observations', 'measurements', 'repair_history')
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024


class Provenance(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['user', 'user_measurement', 'direct_observation', 'official_reference', 'crew_chief', 'model']
    reference: str = Field(min_length=1, max_length=2000)
    run_id: str | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=32)
    supporting_fact_ids: list[str] = Field(default_factory=list, max_length=32)


class RecordInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Literal['facts', 'observations', 'measurements', 'repair_history'] = 'facts'
    subject: str = Field(min_length=1, max_length=300)
    value: str = Field(min_length=1, max_length=2000)
    unit: str = Field(default='', max_length=80)
    status: STATUSES
    provenance: Provenance

    @model_validator(mode='after')
    def status_matches_source(self):
        if self.status == 'measured' and self.provenance.kind != 'user_measurement':
            raise ValueError('Measured facts require a recorded user measurement')
        if self.status == 'verified' and self.provenance.kind != 'official_reference':
            raise ValueError('Verified facts require an explicit official reference')
        return self


class CasePersistence(AtomicJsonModelMixPersistence):
    def __init__(self, root, *, legacy):
        super().__init__(root)
        self.legacy = legacy
        self.objects = self.root.parent / 'objects'

    def _path(self, session_id):
        super()._path(session_id)  # preserve the existing ID/path validation
        return self.root / session_id / 'case.json'

    @staticmethod
    def _session_id_for_path(path):
        return path.parent.name

    @staticmethod
    def _validate(value):
        AtomicJsonModelMixPersistence._validate(value)
        case = value.get('case')
        if not isinstance(case, dict) or case.get('case_id') != value['session']['session_id']:
            raise PersistenceError('Malformed Case identity')
        if not isinstance(case.get('name'), str) or not case['name'].strip() or not isinstance(case.get('revision'), int):
            raise PersistenceError('Malformed Case metadata')
        for category in CATEGORIES:
            if not isinstance(case.get(category), list):
                raise PersistenceError('Malformed Case records')
            for record in case[category]:
                RecordInput.model_validate({key: val for key, val in record.items() if key not in {'fact_id', 'created_at'}})

    def _new_document(self, name, case_id=None):
        name = name.strip()
        if not name or len(name) > 160:
            raise ValueError('Case name must contain 1–160 characters')
        cid = case_id or str(uuid.uuid4())
        now = time.time()
        return {'schema_version': 1,
                'case': {'case_id': cid, 'name': name, 'created_at': now, 'updated_at': now,
                         'revision': 1, 'machine': {}, **{key: [] for key in CATEGORIES},
                         'attachments': [], 'accepted_promotions': [], 'imported_from': None},
                'session': {'session_id': cid, 'created_at': now, 'updated_at': now, 'messages': [], 'runs': []}}

    async def create_case(self, name, case_id=None):
        async with self._lock:
            doc = self._new_document(name, case_id)
            path = self._path(doc['case']['case_id'])
            if path.exists():
                raise PersistenceError('Case already exists')
            self._write_atomic(path, doc)
            return deepcopy(doc)

    async def create_session(self, session_id):
        if self._path(session_id).exists():
            return await self.load_session(session_id)
        if await self.legacy.load_session(session_id) is not None:
            raise PersistenceError('Legacy sessions are read-only; import into a Case first')
        return await self.create_case('Repair case', session_id)

    async def load_session(self, session_id):
        if self._path(session_id).exists():
            return await super().load_session(session_id)
        return await self.legacy.load_session(session_id)

    def _case_documents(self):
        return [self._read(path) for path in self.root.glob('*/case.json')]

    async def list_cases(self):
        async with self._lock:
            return sorted([{'case_id': doc['case']['case_id'], 'name': doc['case']['name'],
                            'updated_at': doc['session']['updated_at'], 'revision': doc['case']['revision'],
                            'run_count': len(doc['session']['runs']), 'created_at': doc['case']['created_at'],
                            'message_count': len(doc['session']['messages'])} for doc in self._case_documents()],
                          key=lambda item: item['updated_at'], reverse=True)

    async def list_sessions(self):
        cases = await self.list_cases()
        return sorted([*({'session_id': c['case_id'], 'name': c['name'], 'updated_at': c['updated_at'], 'created_at': c['created_at'], 'message_count': c['message_count'], 'is_case': True}
                         for c in cases), *await self.legacy.list_sessions()], key=lambda s: s['updated_at'], reverse=True)

    async def latest_session(self):
        sessions = await self.list_sessions()
        return await self.load_session(sessions[0]['session_id']) if sessions else None

    async def find_run(self, run_id):
        async with self._lock:
            for doc in self._case_documents():
                run = next((r for r in doc['session']['runs'] if r['run_id'] == run_id), None)
                if run is not None:
                    return deepcopy(doc), deepcopy(run)
        return await self.legacy.find_run(run_id)

    async def delete_session(self, session_id):
        raise PersistenceError('Cases and legacy sessions cannot be deleted through the legacy session route')

    def _load_case(self, case_id):
        doc = self._read(self._path(case_id), missing_ok=True)
        if doc is None:
            raise PersistenceError('Case not found; legacy sessions must be imported first')
        return doc

    def _save_case_update(self, doc):
        doc['case']['revision'] += 1
        doc['case']['updated_at'] = doc['session']['updated_at'] = time.time()
        self._write_atomic(self._path(doc['case']['case_id']), doc)
        return deepcopy(doc)

    async def update_case(self, case_id, *, name=None, machine=None):
        async with self._lock:
            doc = self._load_case(case_id)
            if name is not None:
                clean = name.strip()
                if not clean or len(clean) > 160:
                    raise ValueError('Case name must contain 1–160 characters')
                doc['case']['name'] = clean
            if machine is not None:
                if len(machine) > 30 or not all(isinstance(k, str) and isinstance(v, str) and len(k) <= 100 and len(v) <= 500 for k, v in machine.items()):
                    raise ValueError('Machine identity must be a small string mapping')
                doc['case']['machine'] = dict(machine)
            return self._save_case_update(doc)

    async def add_record(self, case_id, value):
        record = RecordInput.model_validate(value).model_dump()
        async with self._lock:
            doc = self._load_case(case_id)
            doc['case'][record['category']].append({**record, 'fact_id': str(uuid.uuid4()), 'created_at': time.time()})
            return self._save_case_update(doc)

    async def create_run(self, session_id, run):
        async with self._lock:
            doc = self._load_case(session_id)
            if any(prior['run_id'] == run['run_id'] for prior in doc['session']['runs']):
                raise PersistenceError('Run already exists')
            snapshot = {key: deepcopy(doc['case'][key]) for key in ['case_id', 'name', 'revision', 'machine', *CATEGORIES, 'attachments']}
            snapshot.update(question=run['prompt'], captured_at=time.time())
            doc['session']['runs'].append({**deepcopy(run), 'case_snapshot': snapshot})
            doc['session']['messages'].append({'message_id': f"{run['run_id']}:user", 'run_id': run['run_id'],
                                               'seat': 'shared', 'audience': ['worker_a', 'worker_b', 'moderator'],
                                               'role': 'user', 'content': run['prompt']})
            doc['session']['updated_at'] = time.time()
            self._write_atomic(self._path(session_id), doc)

    async def import_legacy(self, session_id, name='Imported repair case'):
        legacy = await self.legacy.load_session(session_id)
        if legacy is None:
            raise PersistenceError('Legacy session not found')
        if any(r['status'] not in {'completed', 'partial', 'failed', 'cancelled'} for r in legacy['session']['runs']):
            raise PersistenceError('Legacy session has an unfinished run; import requires terminal records')
        async with self._lock:
            for prior in self._case_documents():
                if prior['case'].get('imported_from') == session_id:
                    return deepcopy(prior)
            doc = self._new_document(name)
            doc['case']['imported_from'] = session_id
            doc['session']['messages'] = deepcopy(legacy['session']['messages'])
            doc['session']['runs'] = deepcopy(legacy['session']['runs'])
            self._write_atomic(self._path(doc['case']['case_id']), doc)
            return deepcopy(doc)

    async def add_attachment(self, case_id, filename, content, media_type):
        if not content or len(content) > MAX_ATTACHMENT_BYTES:
            raise ValueError('Attachments must contain 1–8388608 bytes')
        digest = hashlib.sha256(content).hexdigest()
        async with self._lock:
            doc = self._load_case(case_id)
            self.objects.mkdir(parents=True, exist_ok=True)
            path = self.objects / digest
            if path.exists():
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise PersistenceError('Attachment cache integrity check failed')
            else:
                fd, temporary = tempfile.mkstemp(prefix='.attachment-', dir=self.objects)
                try:
                    with os.fdopen(fd, 'wb') as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary, path)
                    if os.name != 'nt':
                        directory = os.open(self.objects, os.O_RDONLY)
                        try:
                            os.fsync(directory)
                        finally:
                            os.close(directory)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            if not any(a['sha256'] == digest for a in doc['case']['attachments']):
                doc['case']['attachments'].append({'sha256': digest, 'filename': Path(filename.replace('\\', '/')).name[:200],
                                                   'media_type': media_type[:200], 'size': len(content), 'created_at': time.time()})
            return self._save_case_update(doc)

    async def read_attachment(self, ref, offset=0, limit=12000):
        digest = ref.get('sha256', '')
        if not re.fullmatch('[0-9a-f]{64}', digest) or not isinstance(offset, int) or offset < 0:
            raise PersistenceError('Invalid attachment reference')
        if Path(ref['filename']).suffix.lower() not in {'.txt', '.md', '.csv', '.json', '.log'}:
            raise PersistenceError('Only UTF-8 text resources are readable in this pass')
        data = (self.objects / digest).read_bytes()
        if len(data) > MAX_ATTACHMENT_BYTES or hashlib.sha256(data).hexdigest() != digest:
            raise PersistenceError('Attachment integrity check failed')
        text = data.decode('utf-8')
        return {'source_id': f'attachment:{digest}:{offset}', 'title': ref['filename'], 'reference': digest,
                'url': None, 'kind': 'attachment_text', 'excerpt': text[offset:offset + limit],
                'offset': offset, 'next_offset': offset + limit if offset + limit < len(text) else None}

    async def accept_promotion(self, case_id, run_id, candidate_id):
        """Accept only a saved completed Chief proposal, with status/source guards."""
        from .research import sources_from
        async with self._lock:
            doc = self._load_case(case_id)
            if any(p['run_id'] == run_id and p['candidate_id'] == candidate_id for p in doc['case']['accepted_promotions']):
                return deepcopy(doc)
            run = next((r for r in doc['session']['runs'] if r['run_id'] == run_id), None)
            chief = next((m for m in doc['session']['messages'] if m['run_id'] == run_id and m['seat'] == 'moderator'), None)
            if run is None or run['status'] not in {'completed', 'partial'} or not chief or chief.get('status') != 'completed' or not chief.get('content'):
                raise PersistenceError('Only completed Crew Chief rulings may promote Case information')
            candidate = next((p for p in chief.get('promotions', []) if p.get('candidate_id') == candidate_id), None)
            if candidate is None:
                raise PersistenceError('Saved Crew Chief proposal not found')
            subject, value, unit = candidate.get('subject'), candidate.get('value'), candidate.get('unit', '')
            status = candidate.get('status')
            if status not in {'crew_chief_accepted', 'measured', 'verified', 'hypothesis', 'disputed', 'unresolved', 'rejected'}:
                raise ValueError('Invalid promotion status')
            snapshot = run.get('case_snapshot', {})
            facts = [r for key in CATEGORIES for r in snapshot.get(key, [])]
            supporting = candidate.get('supporting_fact_ids', [])
            matching = [r for r in facts if r['fact_id'] in supporting and r['subject'] == subject and r['value'] == value and r.get('unit', '') == unit]
            provenance = {'kind': 'crew_chief', 'reference': 'Explicitly accepted Crew Chief proposal',
                          'run_id': run_id, 'source_ids': [], 'supporting_fact_ids': supporting}
            if status in {'measured', 'verified'}:
                original = next((r for r in matching if r['status'] == status), None)
                if original is None:
                    raise ValueError('Model conclusions cannot invent measured or officially verified facts')
                provenance = {**original['provenance'], 'run_id': run_id, 'supporting_fact_ids': supporting}
            elif status == 'crew_chief_accepted':
                original = next((r for r in matching if r['status'] in {'user_reported', 'observed', 'measured', 'verified', 'crew_chief_accepted'}), None)
                if original is None:
                    sources = {s['source_id']: s for event in run['events'] if event['type'] == 'tool_completed' for s in sources_from(event['tool'].get('result'))}
                    findings = {}
                    for event in run['events']:
                        if event['type'] == 'moderator_evidence':
                            findings[event['evidence']['claim_id']] = event['evidence']
                    finding = next((f for f in findings.values() if (f['claim_id'] == candidate.get('finding_id') or f['claim'] == candidate.get('finding_claim'))), None)
                    source = sources.get(candidate.get('source_id'))
                    quote = candidate.get('quote')
                    if not finding or finding['result'] != 'verified' or not source or source.get('kind') == 'case_snapshot' or not isinstance(quote, str) or not quote.strip() or quote not in source['excerpt'] or not isinstance(value, str) or value not in quote or finding.get('source_id') != source['source_id'] or quote != finding.get('quote') or value not in finding['claim']:
                        raise ValueError('Accepted facts require supported frozen facts or a verified, quote-bound Chief finding')
                    provenance.update(reference=quote, source_ids=[source['source_id']])
            record = RecordInput.model_validate({'category': candidate.get('category', 'facts'), 'subject': subject,
                                                 'value': value, 'unit': unit, 'status': status, 'provenance': provenance}).model_dump()
            fact_id = str(uuid.uuid4())
            doc['case'][record['category']].append({**record, 'fact_id': fact_id, 'created_at': time.time()})
            doc['case']['accepted_promotions'].append({'run_id': run_id, 'candidate_id': candidate_id,
                                                     'fact_id': fact_id, 'accepted_at': time.time()})
            return self._save_case_update(doc)

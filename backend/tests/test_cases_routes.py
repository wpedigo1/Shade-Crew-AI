"""Exercise Case HTTP surface and SSE compatibility without external models."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modelmix.cases import CasePersistence
from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.modelmix.registry import RunRegistry
from backend.modelmix.routes import router
from backend.tests.test_case_research import Scripted, Search, finish


def app_for(tmp_path, monkeypatch):
    repo = CasePersistence(tmp_path / 'cases', legacy=AtomicJsonModelMixPersistence(tmp_path / 'sessions'))
    registry = RunRegistry(persistence=repo, research_adapter=Search())
    monkeypatch.setattr('backend.modelmix.routes.run_registry', registry)
    monkeypatch.setattr('backend.modelmix.routes.get_provider_for_model', lambda model: Scripted([finish()]))
    app = FastAPI()
    app.include_router(router)
    return app, repo


def test_create_update_run_reload_and_attachment_routes(tmp_path, monkeypatch):
    app, _ = app_for(tmp_path, monkeypatch)
    with TestClient(app) as client:
        created = client.post('/api/modelmix/cases', json={'name': 'Truck'}).json()
        cid = created['case']['case_id']
        assert client.patch(f'/api/modelmix/cases/{cid}', json={'name': 'No crank', 'machine': {'engine': 'unknown'}}).status_code == 200
        response = client.post(f'/api/modelmix/cases/{cid}/facts', json={'category': 'measurements', 'subject': 'Battery', 'value': '12.6', 'unit': 'V', 'status': 'measured', 'provenance': {'kind': 'user_measurement', 'reference': 'At posts'}})
        assert response.status_code == 200
        attachment = client.post(f'/api/modelmix/cases/{cid}/attachments', files={'file': ('notes.txt', b'Test observation', 'text/plain')})
        assert attachment.status_code == 200
        run = client.post('/api/modelmix/runs/stream', json={'prompt': 'Next test?', 'worker_a_model': 'a', 'worker_b_model': 'b', 'moderator_model': 'm', 'case_id': cid})
        assert run.status_code == 200
        assert 'research_started' in run.text
        assert run.headers['X-ModelMix-Session-ID'] == cid
        doc = client.get(f'/api/modelmix/cases/{cid}').json()
        snap = doc['session']['runs'][0]['case_snapshot']
        assert snap['machine'] == {'engine': 'unknown'}
        assert snap['measurements'][0]['value'] == '12.6'
        assert len(snap['attachments']) == 1
        run_id = run.headers['X-ModelMix-Run-ID']
    fresh_app, _ = app_for(tmp_path, monkeypatch)
    with TestClient(fresh_app) as client:
        assert client.get('/api/modelmix/cases').json()[0]['name'] == 'No crank'
        assert client.get(f'/api/modelmix/cases/{cid}').json()['session']['runs'][0]['case_snapshot'] == snap
        replay = client.get(f'/api/modelmix/runs/{run_id}/events?after_seq=0')
        assert replay.status_code == 200 and 'research_completed' in replay.text


def test_run_without_identity_creates_case(tmp_path, monkeypatch):
    app, _ = app_for(tmp_path, monkeypatch)
    with TestClient(app) as client:
        response = client.post('/api/modelmix/runs/stream', json={'prompt': 'Mower no crank', 'worker_a_model': 'a'})
        assert response.status_code == 200
        assert client.get('/api/modelmix/cases').json()[0]['name'] == 'Mower no crank'


def test_input_validation_and_promotion_cannot_accept_fabricated_request(tmp_path, monkeypatch):
    app, _ = app_for(tmp_path, monkeypatch)
    with TestClient(app) as client:
        cid = client.post('/api/modelmix/cases', json={'name': 'Job'}).json()['case']['case_id']
        assert client.post(f'/api/modelmix/cases/{cid}/facts', json={'subject': 'guess', 'value': 'bad', 'status': 'verified', 'provenance': {'kind': 'model', 'reference': 'thought'}}).status_code == 422
        assert client.post(f'/api/modelmix/cases/{cid}/promotions', json={'run_id': 'made-up', 'candidate_id': 'p1'}).status_code == 422
        assert client.get('/api/modelmix/cases/legacy').status_code == 404

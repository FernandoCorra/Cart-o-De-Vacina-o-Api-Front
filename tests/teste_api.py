from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

# Se você exportou API_KEY no ambiente do backend, preencha aqui também:
HEADERS = {}
if "API_KEY" in os.environ and os.environ["API_KEY"]:
    HEADERS = {"X-API-Key": os.environ["API_KEY"]}

def test_happy_path():
    # cria vacina
    v_resp = client.post("/vaccines", json={
        "name": "Hepatite B", "code": "hepb", "allowed_doses": ["D1","D2","D3","R1"]
    }, headers=HEADERS)
    assert v_resp.status_code == 201, v_resp.text
    v = v_resp.json()

    # cria pessoa
    p_resp = client.post("/people", json={"name":"Ana Paula","document":"123"}, headers=HEADERS)
    assert p_resp.status_code == 201, p_resp.text
    p = p_resp.json()

    # registra D1
    r1 = client.post("/vaccinations", json={
        "person_id": p["id"], "vaccine_id": v["id"], "dose": "D1", "applied_at": "2025-01-10"
    }, headers=HEADERS)
    assert r1.status_code == 201, r1.text

    # tentar repetir D1 → 409
    rdup = client.post("/vaccinations", json={
        "person_id": p["id"], "vaccine_id": v["id"], "dose": "D1", "applied_at": "2025-01-11"
    }, headers=HEADERS)
    assert rdup.status_code == 409, rdup.text

    # registrar D2
    r2 = client.post("/vaccinations", json={
        "person_id": p["id"], "vaccine_id": v["id"], "dose": "D2", "applied_at": "2025-02-10"
    }, headers=HEADERS)
    assert r2.status_code == 201, r2.text

    # ver cartão matrix
    cm = client.get(f"/people/{p['id']}/card", params={"format":"matrix"}, headers=HEADERS)
    assert cm.status_code == 200, cm.text

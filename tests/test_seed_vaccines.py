# tests/test_seed_vaccines.py
VACCINES = [
    ("BCG", "bcg"),
    ("HEPATITE B", "hepatite-b"),
    ("ANTI-PÓLIO (SABIN)", "anti-polio-sabin"),
    ("TETRA VALENTE", "tetra-valente"),
    ("TRÍPLICE BACTERIANA (DPT)", "triplice-bacteriana-dpt"),
    ("HAEMOPHILUS INFLUENZAE", "haemophilus-influenzae"),
    ("TRÍPLICE ACELULAR", "triplice-acelular"),
    ("PNEUMO 10 VALENTE", "pneumo-10-valente"),
    ("MENINGO C", "meningo-c"),
    ("ROTAVÍRUS", "rotavirus"),
]

def test_seed_all_vaccines(client):
    # cria todas
    for name, code in VACCINES:
        r = client.post("/vaccines", json={"name": name, "code": code})
        assert r.status_code == 201, f"Falhou criar {name}: {r.status_code} {r.text}"
        body = r.json()
        assert body["code"] == code

    # confere se estao listadas
    r = client.get("/vaccines")
    assert r.status_code == 200
    lst = r.json()
    codes = {v["code"] for v in lst}
    expected = {code for _, code in VACCINES}
    assert expected.issubset(codes), f"Esperado {expected}, obtido {codes}"

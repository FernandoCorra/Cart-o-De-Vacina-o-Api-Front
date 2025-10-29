# scripts/seed_vaccines.py
"""Seed das vacinas usando a API em execução.

Uso:
    export API_BASE=http://localhost:8000
    export API_KEY=segr3do   # (opcional)
    python scripts/seed_vaccines.py
"""

import os, sys, json, urllib.request

API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("API_KEY", None)

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

def post_json(path, payload):
    url = f"{API_BASE}{path}"
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 409:  # já existe
            return e.code, {"detail": "conflict (já existia)"}
        txt = e.read().decode("utf-8", errors="ignore")
        return e.code, {"error": txt or e.reason}
    except Exception as e:
        return 0, {"error": str(e)}

def get_json(path):
    url = f"{API_BASE}{path}"
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print(f"[seed] Base: {API_BASE}")
    created = 0
    for name, code in VACCINES:
        status, data = post_json("/vaccines", {"name": name, "code": code})
        if status in (200, 201):
            created += 1
            print(f"  + {name} ({code}) -> OK")
        elif status == 409:
            print(f"  = {name} ({code}) -> já existia")
        else:
            print(f"  ! {name} ({code}) -> ERRO {status}: {data}")

    lst = get_json("/vaccines")
    codes = {v["code"] for v in lst}
    missing = [c for _, c in VACCINES if c not in codes]
    if missing:
        print(f"[seed] Faltando criar: {missing}")
        sys.exit(2)

    print(f"[seed] Finalizado. Total no catálogo: {len(lst)} (criados nesta execução: {created}).")

if __name__ == "__main__":
    main()

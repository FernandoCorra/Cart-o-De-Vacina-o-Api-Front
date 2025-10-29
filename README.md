# Cartão de Vacinação – FastAPI (backend) + Front (Vite/React)

Este repositório contém:
- **Backend** em FastAPI (`main.py`) com SQLite (`vaccines.db`).
- **Frontend** (pasta `vacina-frontend`) usando Vite/React.

A API implementa:
- **Vacinas** (`/vaccines`)
- **Pessoas** (`/people`)
- **Registros de vacinação** (`/vaccinations`)
- **Cartão** por pessoa, em **lista** ou **matriz** (`/people/{pid}/card?format=list|matrix`)

O **acesso** é protegido por **API Key opcional** via header `X-API-Key` quando a variável de ambiente `API_KEY` estiver definida.

---

## Sumário

- [Stack](#stack)
- [Estrutura](#estrutura)
- [Setup backend](#setup-backend)
- [Executando o backend](#executando-o-backend)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Referência de API](#referência-de-api)
  - [Saúde](#saúde)
  - [Vacinas](#vacinas)
  - [Pessoas](#pessoas)
  - [Vacinações](#vacinações)
  - [Cartão](#cartão)
  - [Erros](#erros)
- [Regras de negócio](#regras-de-negócio)
- [CORS](#cors)
- [Testes](#testes)
- [Frontend](#frontend)
- [Notas de projeto](#notas-de-projeto)

---

## Stack

- **Python** 3.10+ (testado com 3.11)
- **FastAPI** + **Uvicorn**
- **SQLAlchemy** + **SQLite**
- **Pydantic**
- **Pytest** (testes)

---

## Estrutura

```
.
├── main.py                  # FastAPI + SQLAlchemy
├── vaccines.db              # (criado automaticamente ao rodar)
├── tests/
│   ├── conftest.py          # overrides e DB de teste
│   ├── test_people.py       # testes: criar/listar pessoa
│   └── test_vaccines.py     # testes: criar/listar vacina
└── vacina-frontend/         # Vite/React (conforme imagem)
    ├── node_modules/ …
    ├── public/
    ├── src/
    ├── index.html
    ├── package.json
    └── vite.config.ts
```

> Se a pasta `tests/` ainda não existir, ela é criada neste pacote com exemplos funcionais.

---

## Setup backend

Crie um ambiente virtual e instale as dependências:

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install fastapi uvicorn sqlalchemy pydantic pytest
```

> O banco **SQLite** é criado automaticamente como `vaccines.db` na raiz quando a API sobe.

---

## Executando o backend

```bash
uvicorn main:app --reload --port 8000
# Documentação: http://localhost:8000/docs
```

Se você definir `API_KEY`, as chamadas devem enviar o header `X-API-Key` com o mesmo valor.

Exemplo cURL:

```bash
curl -H "X-API-Key: segr3do" http://localhost:8000/health
```

---

## Variáveis de ambiente

- `API_KEY` – se definida, obriga enviar `X-API-Key` em todas as rotas (exceto `/health`).

No Linux/Mac:

```bash
export API_KEY=segr3do
```

No Windows (PowerShell):

```powershell
$env:API_KEY="segr3do"
```

---

## Referência de API

### Saúde

- `GET /health` → `{ "status": "ok" }`

### Vacinas

- **POST** `/vaccines` (criar)
  ```json
  {
    "name": "Hepatite B",
    "code": "hepb",
    "allowed_doses": ["D1", "D2", "D3", "R1", "R2"]
  }
  ```
  - `code` é **único** (slug).  
  - `allowed_doses` é opcional (por padrão: `["D1","D2","D3","R1","R2"]`).

- **GET** `/vaccines` (listar)

- **GET** `/vaccines/{id}` (buscar por id)

- **DELETE** `/vaccines/{id}` (apagar)

### Pessoas

- **POST** `/people` (criar)
  ```json
  {
    "name": "Ana Souza",
    "document": "12345678900"
  }
  ```
  - `document` é **único**.

- **GET** `/people` (listar)

- **GET** `/people/{id}` (buscar por id)

- **DELETE** `/people/{id}` (apagar; deleção em cascata remove vacinações)

### Vacinações

- **POST** `/vaccinations` (criar)
  ```json
  {
    "person_id": "<uuid-pessoa>",
    "vaccine_id": "<uuid-vacina>",
    "dose": "D1",
    "applied_at": "2025-10-29",
    "lot": "L123",
    "location": "UBS Central"
  }
  ```
  - Valida dose permitida para a vacina.
  - Por padrão, **exige ordem** (D1 antes de D2, etc.). Para desativar: `?enforce_sequence=false`.

- **GET** `/vaccinations/{id}` (buscar por id)

- **DELETE** `/vaccinations/{id}` (apagar)

### Cartão

- **GET** `/people/{pid}/card?format=list|matrix`  
  - `format=list`: agrupado por vacina, com entradas.  
  - `format=matrix`: matriz Dose × Vacina (célula = registro).

### Erros

- `400/409/422` – validações e conflitos (ex.: `code`/`document` duplicados, dose fora da ordem).  
- `401` – API Key ausente/errada quando `API_KEY` está setada.  
- `404` – não encontrado.

---

## Regras de negócio

- **Dose permitida**: a dose enviada deve existir em `allowed_doses` da vacina.
- **Ordem de doses**: por padrão, requer D1→D2→D3→R1→R2. Param `enforce_sequence=false` desliga.
- **Unicidade por pessoa/vacina/dose**: um trio `(person_id, vaccine_id, dose)` é único.

---

## CORS

Liberado para todos (`allow_origins=["*"]`) no `main.py`. Ajuste em produção.

---

## Testes

Fornecemos testes **funcionais** para **adicionar vacina** e **adicionar pessoa**. Eles criam um banco **temporário** e sobrescrevem as dependências de DB e API Key.

### Instalação (se necessário)

```bash
pip install pytest
```

### Rodando

```bash
pytest -q
```

> Os testes usam `TestClient` do FastAPI e não exigem subir o servidor.

---

## Frontend

A pasta `vacina-frontend/` (Vite/React) pode consumir esta API. Para rodar:

```bash
cd vacina-frontend
npm install
npm run dev
# http://localhost:5173
```

No cliente, ao chamar a API com `fetch`/Axios, inclua `X-API-Key` se `API_KEY` estiver configurada no backend.

---

## Notas de projeto

- **SQLite + PRAGMA foreign_keys**: habilitado para suportar `ON DELETE CASCADE`.  
- **Schema**: `Vaccine`, `Person`, `Vaccination` com constraints e `UniqueConstraint(person_id, vaccine_id, dose)`.  
- **Card**: duas visualizações (lista/matriz) para atender diferentes UIs.

# Cartão de Vacinação – API + Front

Sistema para **consulta do cartão de vacinação** e **cadastro de vacinas/vacinações**.  
Arquitetura: **Front (SPA)** + **API REST** + **Banco de dados**.

> **Decisão arquitetural:** consulta e cadastro coexistem no **mesmo front** (rotas distintas), consumindo a **mesma API** com controle de acesso por perfil (RBAC).

---

## Sumário

- [Visão geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Stack técnica](#stack-técnica)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Modelagem de dados](#modelagem-de-dados)
- [Setup local](#setup-local)
- [Executando](#executando)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [API – Referência](#api--referência)
  - [Autenticação](#autenticação)
  - [Pessoas](#pessoas)
  - [Vacinas](#vacinas)
  - [Vacinações](#vacinações)
  - [Cartão de vacinação](#cartão-de-vacinação)
  - [Erros](#erros)
- [Validações de negócio](#validações-de-negócio)
- [Segurança](#segurança)
- [Observabilidade](#observabilidade)
- [Testes](#testes)
- [CI/CD (opcional)](#cicd-opcional)
- [Decisões arquiteturais (ADR)](#decisões-arquiteturais-adr)
- [Guia de Git e commits](#guia-de-git-e-commits)
- [Changelog](#changelog)

---

## Visão geral

Este projeto implementa um sistema de **Cartão de Vacinação** com:
- **Consulta** do histórico de vacinações de uma pessoa;
- **Cadastro** de vacinas e registro de **vacinações** com validações de negócio (intervalo mínimo, número de doses, unicidade de dose por pessoa/vacina).

O **front-end** (SPA) concentra **consulta** e **cadastro** em rotas distintas e consome a **mesma API REST**. O **back-end** aplica autenticação via **JWT**, autorização por **RBAC**, validação de payloads e logging estruturado.

---

## Arquitetura

```
[ Front SPA ] ─── HTTP/JSON ───> [ API REST (v1) ] ─── SQL ───> [ Banco de Dados ]
     |                                |
  Rotas /consulta e /cadastro         └── JWT/RBAC, validação, logs, métricas
```

- **Front (SPA)**: telas separadas para consulta (`/consulta`) e cadastro (`/cadastro`).
- **API REST (v1)**: endpoints idempotentes, OpenAPI automático, padronização de erros.
- **Banco de dados**: persistência de pessoas, vacinas e vacinações com integridade referencial.

---

## Stack técnica

- **Back-end**: Python + **FastAPI** (pode ser adaptado para Flask); OpenAPI/Swagger nativo
- **DB**: SQLite (dev) / PostgreSQL (prod)
- **Auth**: JWT (Access/Refresh) + **RBAC**
- **Front**: React + Vite (ou framework equivalente)
- **Migrações**: Alembic (Postgres) / SQL simples (SQLite)
- **Testes**: Pytest + HTTPX

> Se optar por Flask, os conceitos e rotas permanecem; apenas mudam os detalhes de execução e dependências.

---

## Estrutura do repositório

```
.
├── api/
│   ├── app.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── pessoas.py
│   │   ├── vacinas.py
│   │   └── vacinacoes.py
│   ├── models.py
│   ├── schemas.py
│   ├── services/
│   │   └── validacao_doses.py
│   ├── db.py
│   └── settings.py
├── frontend/
│   ├── src/
│   │   ├── pages/Consulta.tsx
│   │   ├── pages/Cadastro.tsx
│   │   └── services/api.ts
│   └── vite.config.ts
├── docs/
│   ├── ADR-0001-spa-unica.md
│   └── postman_collection.json (exemplo)
├── scripts/
│   ├── dev.sh
│   └── seed_db.py
├── tests/
│   ├── test_auth.py
│   ├── test_pessoas.py
│   ├── test_vacinas.py
│   └── test_vacinacoes.py
├── .env.example
├── .gitignore
└── README.md
```

---

## Modelagem de dados

**Entidades**

- `pessoas(id TEXT PK, nome TEXT NOT NULL, created_at DATETIME)`
- `vacinas(id TEXT PK, nome TEXT NOT NULL, doses_totais INT, intervalo_min_dias INT, created_at DATETIME)`
- `vacinacoes(id INTEGER PK AUTOINCREMENT, pessoa_id TEXT FK, vacina_id TEXT FK, dose INT, data_aplicacao DATE, created_at DATETIME)`

**Regras**
- `vacinacoes.pessoa_id` → `pessoas.id` (**ON DELETE CASCADE**)
- `vacinacoes.vacina_id` → `vacinas.id`
- Índices em `vacinacoes(pessoa_id)` e `vacinacoes(vacina_id)`

**ERD**

```
pessoas (1) ───< (n) vacinacoes (n) >─── (1) vacinas
```

---

## Setup local

1) **Clonar o repositório**
```bash
git clone https://github.com/seu-usuario/cartao-vacinacao.git
cd cartao-vacinacao
```

2) **Criar venv e instalar dependências (API)**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn pydantic[dotenv] python-multipart python-jose[cryptography] passlib[bcrypt] sqlalchemy aiosqlite httpx pytest
```

3) **Configurar variáveis**
```bash
cp .env.example .env
# Edite JWT_SECRET, DATABASE_URL, CORS_ORIGINS etc.
```

4) **Inicializar DB (SQLite)**
```bash
python scripts/seed_db.py
```

5) **Instalar front**
```bash
cd frontend
npm i
cd ..
```

---

## Executando

**API**
```bash
uvicorn api.app:app --reload --port 8000
# OpenAPI/Swagger: http://localhost:8000/docs
```

**Front**
```bash
cd frontend
npm run dev
# http://localhost:5173
```

---

## Variáveis de ambiente

```
APP_ENV=dev
DATABASE_URL=sqlite+aiosqlite:///./app.db
JWT_SECRET=troque-por-um-segredo-longo
ACCESS_TOKEN_EXPIRES_MIN=15
REFRESH_TOKEN_EXPIRES_MIN=43200
CORS_ORIGINS=http://localhost:5173
```

> Para Postgres, use `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname` e configure Alembic.

---

## API – Referência

Base URL: `/api/v1`  
Autenticação: `Authorization: Bearer <access_token>`

### Autenticação

- **POST** `/auth/login`  
  **Body**
  ```json
  { "username": "admin", "password": "..." }
  ```
  **200**
  ```json
  { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }
  ```

- **POST** `/auth/refresh`  
  **Body**
  ```json
  { "refresh_token": "..." }
  ```
  **200**
  ```json
  { "access_token": "...", "token_type": "bearer" }
  ```

---

### Pessoas

- **POST** `/pessoas` – criar pessoa
  ```json
  { "id": "123", "nome": "Ana Souza" }
  ```
  **201**
  ```json
  { "id": "123", "nome": "Ana Souza", "created_at": "2025-10-29T10:00:00Z" }
  ```

- **DELETE** `/pessoas/{id}` – remover pessoa (e seu cartão de vacinação por cascata)  
  **204** (sem corpo)

---

### Vacinas

- **POST** `/vacinas` – criar vacina
  ```json
  {
    "id": "covid_bnt",
    "nome": "COVID-19 (BNT)",
    "doses_totais": 2,
    "intervalo_min_dias": 21
  }
  ```
  **201**
  ```json
  {
    "id": "covid_bnt",
    "nome": "COVID-19 (BNT)",
    "doses_totais": 2,
    "intervalo_min_dias": 21,
    "created_at": "2025-10-29T10:00:00Z"
  }
  ```

- **GET** `/vacinas?search=covid` – listar/filtrar  
  **200**: `[{...}, ...]`

---

### Vacinações

- **POST** `/vacinacoes` – registrar vacinação
  ```json
  {
    "pessoa_id": "123",
    "vacina_id": "covid_bnt",
    "dose": 1,
    "data_aplicacao": "2025-10-26"
  }
  ```
  **201**
  ```json
  {
    "id": 10,
    "pessoa_id": "123",
    "vacina_id": "covid_bnt",
    "dose": 1,
    "data_aplicacao": "2025-10-26",
    "created_at": "2025-10-29T10:00:00Z"
  }
  ```

- **DELETE** `/vacinacoes/{id}` – excluir registro de vacinação  
  **204** (sem corpo)

---

### Cartão de vacinação

- **GET** `/pessoas/{id}/cartao` – consultar cartão
  **200**
  ```json
  {
    "pessoa": { "id": "123", "nome": "Ana Souza" },
    "registros": [
      {
        "vacina": {
          "id": "covid_bnt",
          "nome": "COVID-19 (BNT)",
          "doses_totais": 2,
          "intervalo_min_dias": 21
        },
        "dose": 1,
        "data_aplicacao": "2025-10-26"
      }
    ]
  }
  ```

---

### Erros

- **400 Bad Request** – payload/regra inválidos  
- **401 Unauthorized** – token ausente/expirado  
- **403 Forbidden** – sem permissão (RBAC)  
- **404 Not Found** – recurso inexistente  
- **409 Conflict** – violação de regra de negócio (ex.: dose repetida)  
- **422 Unprocessable Entity** – schema inválido  
- **429 Too Many Requests** – rate limit  
- **500 Internal Server Error** – erro não mapeado  

**Formato padrão**
```json
{
  "error": "business_rule_violation",
  "message": "Dose 2 inválida: intervalo mínimo de 21 dias não cumprido",
  "details": { "dias_decorridos": 14, "minimo": 21 }
}
```

---

## Validações de negócio

1. **Intervalo mínimo entre doses**: respeitar `intervalo_min_dias` quando definido.  
2. **Número máximo de doses**: não permitir `dose > doses_totais` quando definido.  
3. **Unicidade de dose**: uma `(pessoa_id, vacina_id, dose)` não pode se repetir.  
4. **Consistência de datas**: `data_aplicacao` não pode ser futura (configurável).

---

## Segurança

- **JWT** com expiração curta (access) e refresh token;
- **RBAC** (ex.: `admin`, `operador`, `leitor`);
- **CORS** restrito ao domínio do front;
- **Rate limiting** (ex.: 100 req/15min por IP);
- **Auditoria**: log de `user_id`, rota, status e latência.

---

## Observabilidade

- **Logs estruturados** (JSON): nível, timestamp, rota, correlação;
- **Métricas**: contadores por rota/status, latências p95/p99;
- **Tracing** (opcional): OpenTelemetry.

---

## Testes

- **Unitários**: validações de regras (intervalo, doses, unicidade);
- **Integração**: rotas (HTTP 200/4xx), autenticação, RBAC;
- **Contrato**: schemas com pydantic.

Execução:
```bash
pytest -q
```

---

## CI/CD (opcional)

- **CI**: lint + testes a cada PR (GitHub Actions);
- **CD**: deploy automatizado em `main` (tag/release);
- **Versionamento**: prefixo `/api/v1`; breaking changes ⇒ `/v2`.

---

## Decisões arquiteturais (ADR)

**ADR-0001 – SPA única (consulta + cadastro)**  
- **Contexto**: duas funcionalidades acessadas por perfis diferentes.  
- **Decisão**: manter **um único front** com rotas separadas, consumindo a **mesma API** com RBAC.  
- **Alternativas**: 2 SPAs separadas (maior custo de infra e duplicação de componentes).  
- **Consequências**: UX unificada; menor overhead de deploy; CORS simplificado; requer atenção a RBAC/roteamento protegido.

> Salvar como `docs/ADR-0001-spa-unica.md`.

---

## Guia de Git e commits

### Branching

- `main`: produção  
- `dev`: integração contínua  
- `feature/<nome>`: novas features  
- `fix/<nome>`: correções  
- `chore/<nome>`: manutenção/infra

Exemplo:
```bash
git checkout -b feature/cadastro-vacinacao
# ... commits ...
git push origin feature/cadastro-vacinacao
```

### Convenção de commits (Conventional Commits)

Formato:
```
<type>(escopo opcional): descrição no imperativo

[corpo opcional]
[footer opcional]
```

Tipos comuns: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`, `perf`, `style`

Exemplos:
```
feat(api): criar endpoint POST /vacinacoes com validação de dose
fix(db): corrigir cascade delete de pessoa -> vacinações
docs(readme): adicionar exemplos de curl e fluxo de autenticação
```

### Pull Requests

- Descrever **contexto**, **antes/depois** e **prints** (quando front);
- Marcar revisores e garantir que testes passam;
- **Squash merge** (opcional) para histórico limpo;
- Taggear releases (`v1.0.0`, `v1.1.0`) – **SemVer**.

---

## Changelog

Mantenha um `CHANGELOG.md` com entradas por versão (SemVer). Exemplo:

- **[1.0.0] – 2025-10-29**
  - feat: CRUD de pessoas, vacinas e vacinações
  - feat: consulta do cartão de vacinação
  - feat: autenticação JWT + RBAC
  - docs: README inicial



## Exemplos de chamadas (cURL)

**Login**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"senha"}'
```

**Criar pessoa**
```bash
curl -X POST http://localhost:8000/api/v1/pessoas \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"id":"123","nome":"Ana Souza"}'
```

**Registrar vacinação**
```bash
curl -X POST http://localhost:8000/api/v1/vacinacoes \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"pessoa_id":"123","vacina_id":"covid_bnt","dose":1,"data_aplicacao":"2025-10-26"}'
```

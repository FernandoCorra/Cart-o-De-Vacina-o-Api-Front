import React, { useMemo, useState, useEffect } from "react";
import "./app.css";

/**
 * Front ligado na API:
 * - Configura Base URL e X-API-Key
 * - CRUD: Pessoas, Vacinas, Vacinações
 * - Ver cartão matrix (igual ao visual do print)
 * - Clique numa célula preenchida para EXCLUIR aquele registro
 */

// ===== Types =====
type Dose = "D1" | "D2" | "D3" | "R1" | "R2";
type Gender = "M" | "F" | "O";

type MatrixCol = { vaccine_id: string; vaccine_name: string };
type MatrixCell = { record_id: string; applied_at: string; dose: Dose };
type CardMatrix = { rows: Dose[]; cols: MatrixCol[]; grid: (Array<MatrixCell | null>)[] };

// 👇 agora pessoa traz sexo e idade do backend
type Person = { id: string; name: string; document: string; sex: Gender; age: number };
type Vaccine = { id: string; name: string; code: string; allowed_doses: Dose[] };

// ===== UI data (print-like) =====
const DOSES: { code: Dose; labelTop: string; labelBottom: string }[] = [
  { code: "D1", labelTop: "Tipo", labelBottom: "1ª Dose" },
  { code: "D2", labelTop: "Tipo", labelBottom: "2ª Dose" },
  { code: "D3", labelTop: "Tipo", labelBottom: "3ª Dose" },
  { code: "R1", labelTop: "Tipo", labelBottom: "1º Reforço" },
  { code: "R2", labelTop: "Tipo", labelBottom: "2º Reforço" },
];

const VACCINE_HEADERS = [
  "BCG",
  "HEPATITE B",
  "ANTI-PÓLIO\n(SABIN)",
  "TETRA\nVALENTE",
  "TRÍPLICE\nBACTERIANA\n(DPT)",
  "HAEMOPHILUS\nINFLUENZAE",
  "TRÍPLICE\nACELULAR",
  "PNEUMO 10\nVALENTE",
  "MENINGO C",
  "ROTAVÍRUS",
];

const SEX_LABEL: Record<Gender, string> = { F: "FEMININO", M: "MASCULINO", O: "OUTRO" };

// ===== Demo matrix (aparece quando ainda não carregou da API) =====
const demoFilled: Array<[number, number]> = [
  [1, 0],[2, 0],[4, 0],[4, 1],[4, 3],[3, 5],[4, 5],[4, 7],[4, 8],[1, 9],[2, 9],
];
function makeDemoMatrix(): CardMatrix {
  const rows = DOSES.map((d) => d.code) as Dose[];
  const cols: MatrixCol[] = VACCINE_HEADERS.map((name, i) => ({
    vaccine_id: `demo-${i}`, vaccine_name: name
  }));
  const grid: (Array<MatrixCell | null>)[] = rows.map(() => cols.map(() => null));
  demoFilled.forEach(([r, c]) => {
    grid[r][c] = { record_id: `${r}-${c}`, applied_at: "—", dose: rows[r] };
  });
  return { rows, cols, grid };
}

// ===== Helper request =====
async function apiFetch<T>(
  baseURL: string,
  path: string,
  method: "GET" | "POST" | "DELETE" = "GET",
  apiKey?: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${baseURL.replace(/\/$/, "")}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`HTTP ${res.status}: ${txt || res.statusText}`);
  }
  return (await res.json()) as T;
}

// ===== Componente =====
export default function App() {
  // --- Config API ---
  const [baseURL, setBaseURL] = useState<string>("http://localhost:8000");
  const [apiKey, setApiKey] = useState<string>("");

  // --- Pessoas / Vacinas (catálogos) ---
  const [people, setPeople] = useState<Person[]>([]);
  const [vaccines, setVaccines] = useState<Vaccine[]>([]);
  const [selectedPerson, setSelectedPerson] = useState<string>(""); // person_id
  const [selectedVaccine, setSelectedVaccine] = useState<string>(""); // vaccine_id

  // --- Cartão (matrix) ---
  const [matrix, setMatrix] = useState<CardMatrix | null>(null);

  // --- Formularios ---
  const [newPersonName, setNewPersonName] = useState("Ana Paula");
  const [newPersonDoc, setNewPersonDoc] = useState("12345678900");
  // 👇 novos campos para cadastro
  const [newPersonSex, setNewPersonSex] = useState<Gender>("F");
  const [newPersonAge, setNewPersonAge] = useState<number>(18);

  const [newVacName, setNewVacName] = useState("Hepatite B");
  const [newVacCode, setNewVacCode] = useState("hepb");
  const [newVacAllowed, setNewVacAllowed] = useState<Record<Dose, boolean>>({
    D1:true, D2:true, D3:true, R1:true, R2:false
  });

  const [dose, setDose] = useState<Dose>("D1");
  const [date, setDate] = useState<string>(new Date().toISOString().slice(0,10));
  const [lot, setLot] = useState<string>("");
  const [location, setLocation] = useState<string>("UBS Central");

  // --- UI state ---
  const [msg, setMsg] = useState<string>("");
  const [err, setErr] = useState<string>("");

  const demo = useMemo(() => makeDemoMatrix(), []);

  // ========== Actions ==========
  async function loadPeople() {
    try {
      setErr(""); setMsg("Carregando pessoas...");
      const data = await apiFetch<Person[]>(baseURL, "/people", "GET", apiKey);
      setPeople(data);
      setMsg(`Pessoas: ${data.length}`);
      if (!selectedPerson && data.length) setSelectedPerson(data[0].id);
    } catch(e:any) { setErr(e.message); }
  }

  async function loadVaccines() {
    try {
      setErr(""); setMsg("Carregando vacinas...");
      const data = await apiFetch<Vaccine[]>(baseURL, "/vaccines", "GET", apiKey);
      setVaccines(data);
      setMsg(`Vacinas: ${data.length}`);
      if (!selectedVaccine && data.length) setSelectedVaccine(data[0].id);
    } catch(e:any) { setErr(e.message); }
  }

  async function createPerson() {
    try {
      setErr(""); setMsg("Criando pessoa...");
      const p = await apiFetch<Person>(baseURL, "/people", "POST", apiKey, {
        name: newPersonName,
        document: newPersonDoc,
        sex: newPersonSex,        // 👈 envia sexo
        age: newPersonAge         // 👈 envia idade numérica
      });
      setMsg(`Pessoa criada: ${p.name}`);
      await loadPeople();
      setSelectedPerson(p.id);
    } catch(e:any) { setErr(e.message); }
  }

  async function deletePerson() {
    if (!selectedPerson) return;
    if (!confirm("Remover pessoa e todos os registros?")) return;
    try {
      setErr(""); setMsg("Removendo pessoa...");
      await fetch(`${baseURL.replace(/\/$/, "")}/people/${selectedPerson}`, {
        method: "DELETE",
        headers: { ...(apiKey ? {"X-API-Key": apiKey}: {}) }
      }).then(r => { if(!r.ok) throw new Error(`HTTP ${r.status}`); });
      setMsg("Pessoa removida.");
      setSelectedPerson("");
      setMatrix(null);
      await loadPeople();
    } catch(e:any) { setErr(e.message); }
  }

  async function createVaccine() {
    const allowed = (Object.keys(newVacAllowed) as Dose[]).filter(d => newVacAllowed[d]);
    try {
      setErr(""); setMsg("Criando vacina...");
      const v = await apiFetch<Vaccine>(baseURL, "/vaccines", "POST", apiKey, {
        name: newVacName, code: newVacCode, allowed_doses: allowed
      });
      setMsg(`Vacina criada: ${v.name}`);
      await loadVaccines();
      setSelectedVaccine(v.id);
    } catch(e:any) { setErr(e.message); }
  }

  async function loadCard() {
    if (!selectedPerson) { setErr("Selecione uma pessoa."); return; }
    try {
      setErr(""); setMsg("Carregando cartão...");
      const data = await apiFetch<CardMatrix>(
        baseURL, `/people/${selectedPerson}/card?format=matrix`, "GET", apiKey
      );
      data.rows = data.rows.map(r => r.toUpperCase() as Dose);
      setMatrix(data);
      setMsg("Cartão carregado.");
    } catch(e:any) { setErr(e.message); }
  }

  async function registerVaccination() {
    if (!selectedPerson || !selectedVaccine) { setErr("Selecione pessoa e vacina."); return; }
    try {
      setErr(""); setMsg("Registrando vacinação...");
      await apiFetch(baseURL, "/vaccinations", "POST", apiKey, {
        person_id: selectedPerson,
        vaccine_id: selectedVaccine,
        dose, applied_at: date, lot, location
      });
      setMsg("Vacinação registrada.");
      await loadCard();
    } catch(e:any) { setErr(e.message); }
  }

  async function deleteVaccination(recordId: string) {
    if (!confirm("Excluir este registro de vacinação?")) return;
    try {
      setErr(""); setMsg("Excluindo registro...");
      await fetch(`${baseURL.replace(/\/$/, "")}/vaccinations/${recordId}`, {
        method: "DELETE",
        headers: { ...(apiKey ? {"X-API-Key": apiKey}: {}) }
      }).then(r => { if(!r.ok) throw new Error(`HTTP ${r.status}`); });
      setMsg("Registro excluído.");
      await loadCard();
    } catch(e:any) { setErr(e.message); }
  }

  // --------- UI helpers ----------
  const sel = people.find(p => p.id === selectedPerson);
  const ageValue = sel?.age ?? "";
  const sexValue: Gender = sel?.sex ?? "O";

  // ===== Render =====
  const card = matrix ?? demo;
  const vaccineHeaders = matrix ? matrix.cols.map(c => c.vaccine_name) : VACCINE_HEADERS;

  return (
    <div className="page">
      {/* BARRA “Vacina” */}
      <div className="ribbon"><span>Vacina</span></div>

      {/* PAINEL: Config API */}
      <div className="panel">
        <div className="panel-title">Configuração da API</div>
        <div className="panel-form">
          <label className="field" style={{minWidth: 360}}>
            <span>Base URL:</span>
            <input value={baseURL} onChange={(e)=>setBaseURL(e.target.value)} placeholder="http://localhost:8000" />
          </label>
          <label className="field" style={{minWidth: 240}}>
            <span>X-API-Key:</span>
            <input value={apiKey} onChange={(e)=>setApiKey(e.target.value)} placeholder="(opcional)" />
          </label>
          <div className="actions">
            <button className="btn" onClick={loadPeople}>Carregar Pessoas</button>
            <button className="btn" onClick={loadVaccines}>Carregar Vacinas</button>
          </div>
        </div>
        {(msg || err) && (
          <div className={err ? "error" : "notice"}>{err || msg}</div>
        )}
      </div>

      {/* PAINEL: Informações do usuário (visual) */}
      <div className="panel">
        <div className="panel-title">Informações do usuário:</div>
        <div className="panel-form">
          <label className="field" style={{minWidth: 300}}>
            <span>Nome:</span>
            <input value={ sel?.name ?? "" } readOnly />
          </label>
          <label className="field small">
            <span>Idade:</span>
            <input value={ageValue} readOnly />
          </label>
          <label className="field medium">
            <span>Sexo:</span>
            {/* Mantive um select desabilitado, mas agora com valor vindo da API */}
            <select value={sexValue} disabled>
              <option value="F">{SEX_LABEL.F}</option>
              <option value="M">{SEX_LABEL.M}</option>
              <option value="O">{SEX_LABEL.O}</option>
            </select>
          </label>
        </div>
        <div className="more">▼ mais informações</div>
      </div>

      {/* ABAS */}
      <div className="tabs">
        <button className="tab tab-active">Carteira Nacional de Vacinação</button>
        <button className="tab">Anti Rábica</button>
        <button className="tab">BCG de Contato</button>
        <button className="tab">Vacinas Particulares</button>
        <button className="tab">Outra Vacina</button>
      </div>

      {/* TABELA (clicar célula preenchida = excluir registro) */}
      <div className="table-wrapper">
        <div className="table" style={{ gridTemplateColumns: `160px repeat(${vaccineHeaders.length}, 140px)` }}>
          {/* canto */}
          <div className="corner">
            <div className="corner-top">Vacinas</div>
            <div className="corner-bottom">Doses</div>
          </div>

          {/* cabeçalhos de coluna */}
          {vaccineHeaders.map((name, i) => (
            <div key={i} className="col-header">
              {name.split("\n").map((line, idx) => <div key={idx}>{line}</div>)}
            </div>
          ))}

          {/* linhas */}
          {card.rows.map((doseCode, ri) => (
            <React.Fragment key={doseCode}>
              <div className="row-label">
                <div className="row-label-top">{DOSES.find(d=>d.code===doseCode)?.labelTop}</div>
                <div className="row-label-bottom">{DOSES.find(d=>d.code===doseCode)?.labelBottom}</div>
              </div>
              {card.cols.map((_, ci) => {
                const cell = card.grid?.[ri]?.[ci] ?? null;
                const filled = !!cell;
                return (
                  <div
                    key={`${ri}-${ci}`}
                    className={`cell ${filled ? "cell-filled" : ""} ${filled ? "cell-action" : ""}`}
                    title={filled ? `Excluir registro ${cell?.record_id}` : ""}
                    onClick={() => { if (cell?.record_id && matrix) deleteVaccination(cell.record_id); }}
                  />
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* FORMULÁRIOS */}
      <div className="panel">
        <div className="panel-title">1) Pessoas</div>
        <div className="panel-form">
          <label className="field" style={{minWidth: 240}}>
            <span>Nome:</span>
            <input value={newPersonName} onChange={(e)=>setNewPersonName(e.target.value)} />
          </label>
          <label className="field" style={{minWidth: 200}}>
            <span>Documento:</span>
            <input value={newPersonDoc} onChange={(e)=>setNewPersonDoc(e.target.value)} />
          </label>
          {/* NOVOS CAMPOS: sexo e idade */}
          <label className="field small">
            <span>Sexo:</span>
            <select value={newPersonSex} onChange={(e)=>setNewPersonSex(e.target.value as Gender)}>
              <option value="F">{SEX_LABEL.F}</option>
              <option value="M">{SEX_LABEL.M}</option>
              <option value="O">{SEX_LABEL.O}</option>
            </select>
          </label>
          <label className="field small">
            <span>Idade:</span>
            <input
              type="number"
              min={0}
              max={130}
              value={newPersonAge}
              onChange={(e)=>setNewPersonAge(parseInt(e.target.value || "0", 10))}
            />
          </label>

          <div className="actions">
            <button className="btn" onClick={createPerson}>Cadastrar pessoa</button>
            <select
              className="select"
              value={selectedPerson}
              onChange={(e)=>setSelectedPerson(e.target.value)}
            >
              <option value="">— selecione pessoa —</option>
              {people.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.document}) • {SEX_LABEL[p.sex]} • {p.age} anos
                </option>
              ))}
            </select>
            <button className="btn btn-danger" onClick={deletePerson} disabled={!selectedPerson}>Remover pessoa</button>
            <button className="btn btn-primary" onClick={loadCard} disabled={!selectedPerson}>Ver cartão</button>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">2) Vacinas</div>
        <div className="panel-form">
          <label className="field" style={{minWidth: 240}}>
            <span>Nome:</span>
            <input value={newVacName} onChange={(e)=>setNewVacName(e.target.value)} />
          </label>
          <label className="field" style={{minWidth: 180}}>
            <span>Código:</span>
            <input value={newVacCode} onChange={(e)=>setNewVacCode(e.target.value)} />
          </label>

          <div className="dose-box">
            {(["D1","D2","D3","R1","R2"] as Dose[]).map((d)=>(
              <label key={d} className="check">
                <input type="checkbox" checked={!!newVacAllowed[d]} onChange={()=>{
                  setNewVacAllowed(prev=>({...prev, [d]: !prev[d]}));
                }} />
                {d}
              </label>
            ))}
          </div>

          <div className="actions">
            <button className="btn" onClick={createVaccine}>Cadastrar vacina</button>
            <select
              className="select"
              value={selectedVaccine}
              onChange={(e)=>setSelectedVaccine(e.target.value)}
            >
              <option value="">— selecione vacina —</option>
              {vaccines.map(v => <option key={v.id} value={v.id}>{v.name} ({v.code})</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">3) Registrar Vacinação</div>
        <div className="panel-form">
          <label className="field small">
            <span>Dose:</span>
            <select value={dose} onChange={(e)=>setDose(e.target.value as Dose)}>
              {(["D1","D2","D3","R1","R2"] as Dose[]).map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Data:</span>
            <input type="date" value={date} onChange={(e)=>setDate(e.target.value)} />
          </label>
          <label className="field">
            <span>Lote:</span>
            <input value={lot} onChange={(e)=>setLot(e.target.value)} />
          </label>
          <label className="field" style={{minWidth: 240}}>
            <span>Local:</span>
            <input value={location} onChange={(e)=>setLocation(e.target.value)} />
          </label>
          <div className="actions">
            <button className="btn btn-primary" onClick={registerVaccination} disabled={!selectedPerson || !selectedVaccine}>
              Registrar vacinação
            </button>
            <button className="btn" onClick={loadCard} disabled={!selectedPerson}>Atualizar cartão</button>
          </div>
        </div>
        <div className="note-sm">Obs.: ao clicar em uma célula cinza do cartão (carregado da API), o registro é removido.</div>
      </div>

      {/* RODAPÉ DECORATIVO */}
      <div className="footer-icons">
        <button className="icon-btn" title="Voltar">↩</button>
        <button className="icon-btn" title="Baixar">⬇</button>
      </div>
    </div>
  );
}

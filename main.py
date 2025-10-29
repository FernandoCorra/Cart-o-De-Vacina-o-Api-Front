from datetime import date, datetime
import os, uuid, json
from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine, Column, String, Date, DateTime, Text,
    ForeignKey, UniqueConstraint, event, Integer          # <<< import Integer
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session


# ----------------------- Infra / DB -----------------------
DATABASE_URL = "sqlite:///./vaccines.db"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Habilita ON DELETE CASCADE no SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ----------------------- Domain -----------------------
class DoseEnum(str, Enum):
    D1 = "D1"  # 1ª dose
    D2 = "D2"  # 2ª dose
    D3 = "D3"  # 3ª dose
    R1 = "R1"  # 1º reforço
    R2 = "R2"  # 2º reforço

# <<< novo enum para sexo
class GenderEnum(str, Enum):
    M = "M"
    F = "F"
    O = "O"  # Outro/Prefere não informar

DOSE_ORDER = [DoseEnum.D1, DoseEnum.D2, DoseEnum.D3, DoseEnum.R1, DoseEnum.R2]
ORDER_INDEX = {d: i for i, d in enumerate(DOSE_ORDER)}

class Vaccine(Base):
    __tablename__ = "vaccines"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True)
    allowed_doses = Column(Text, nullable=False, default=json.dumps([d.value for d in DOSE_ORDER]))

    vaccinations = relationship("Vaccination", back_populates="vaccine", cascade="all, delete-orphan")

    def allowed_list(self) -> List[str]:
        try:
            return json.loads(self.allowed_doses)
        except Exception:
            return [d.value for d in DOSE_ORDER]

class Person(Base):
    __tablename__ = "people"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    document = Column(String, nullable=False, unique=True)
    # <<< NOVOS CAMPOS
    sex = Column(String, nullable=False)           # "M", "F" ou "O"
    age = Column(Integer, nullable=False)          # idade numérica (anos)

    vaccinations = relationship("Vaccination", back_populates="person", cascade="all, delete-orphan")

class Vaccination(Base):
    __tablename__ = "vaccinations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(String, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    vaccine_id = Column(String, ForeignKey("vaccines.id", ondelete="CASCADE"), nullable=False)
    dose = Column(String, nullable=False)  # stores DoseEnum.value
    applied_at = Column(Date, nullable=False)
    lot = Column(String, nullable=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    person = relationship("Person", back_populates="vaccinations")
    vaccine = relationship("Vaccine", back_populates="vaccinations")

    __table_args__ = (
        UniqueConstraint("person_id", "vaccine_id", "dose", name="uq_person_vaccine_dose"),
    )

Base.metadata.create_all(bind=engine)

# ----------------------- Schemas -----------------------
class VaccineIn(BaseModel):
    name: str
    code: str = Field(..., description="slug único, ex.: hepb")
    allowed_doses: Optional[List[DoseEnum]] = None

class VaccineOut(BaseModel):
    id: str
    name: str
    code: str
    allowed_doses: List[DoseEnum]

    @staticmethod
    def from_model(v: Vaccine) -> "VaccineOut":
        return VaccineOut(
            id=v.id, name=v.name, code=v.code,
            allowed_doses=[DoseEnum(d) for d in v.allowed_list()],
        )

# <<< PersonIn agora pede sexo e idade (inteiro)
class PersonIn(BaseModel):
    name: str
    document: str
    sex: GenderEnum
    age: int = Field(..., ge=0, le=130)

class PersonOut(BaseModel):
    id: str
    name: str
    document: str
    sex: GenderEnum
    age: int

class VaccinationIn(BaseModel):
    person_id: str
    vaccine_id: str
    dose: DoseEnum
    applied_at: date
    lot: Optional[str] = None
    location: Optional[str] = None

class VaccinationOut(BaseModel):
    id: str
    person_id: str
    vaccine_id: str
    dose: DoseEnum
    applied_at: date
    lot: Optional[str]
    location: Optional[str]
    created_at: datetime

# Card (list format)
class CardEntry(BaseModel):
    record_id: str
    dose: DoseEnum
    applied_at: date
    lot: Optional[str] = None
    location: Optional[str] = None

class CardVaccineBlock(BaseModel):
    vaccine_id: str
    vaccine_name: str
    entries: List[CardEntry]

class CardListOut(BaseModel):
    person: PersonOut
    vaccines: List[CardVaccineBlock]

# Card (matrix format)
class MatrixCol(BaseModel):
    vaccine_id: str
    vaccine_name: str

class MatrixCell(BaseModel):
    record_id: str
    applied_at: date
    dose: DoseEnum

class CardMatrixOut(BaseModel):
    rows: List[DoseEnum]
    cols: List[MatrixCol]
    grid: List[List[Optional[MatrixCell]]]  # grid[r][c]

# ----------------------- App / Auth -----------------------
app = FastAPI(title="Cartão de Vacinação API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

API_KEY_ENV = os.getenv("API_KEY")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    # Se API_KEY estiver configurada no ambiente, exija o header correspondente
    if API_KEY_ENV and x_api_key != API_KEY_ENV:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")

@app.get("/health")
async def health():
    return {"status": "ok"}

# ----------------------- Helpers -----------------------
def ensure_dose_allowed(vac: Vaccine, dose: DoseEnum):
    if dose.value not in vac.allowed_list():
        raise HTTPException(status_code=422, detail=f"Dose {dose} não permitida para a vacina {vac.name}")

def ensure_dose_order(db: Session, person_id: str, vaccine_id: str, dose: DoseEnum):
    # Exige que todas as doses anteriores existam
    idx = ORDER_INDEX[dose]
    if idx == 0:
        return
    prev = DOSE_ORDER[:idx]
    existing = {
        r.dose for r in db.query(Vaccination)
        .filter_by(person_id=person_id, vaccine_id=vaccine_id)
        .all()
    }
    for d in prev:
        if d.value not in existing:
            raise HTTPException(
                status_code=409,
                detail=f"Ordem inválida: {dose} requer {d} previamente"
            )

# ----------------------- Endpoints: Vaccines -----------------------
@app.post("/vaccines", response_model=VaccineOut, dependencies=[Depends(require_api_key)], status_code=201)
def create_vaccine(payload: VaccineIn, db: Session = Depends(get_db)):
    if db.query(Vaccine).filter_by(code=payload.code).first():
        raise HTTPException(status_code=409, detail="code já existe")
    allowed = [d.value for d in (payload.allowed_doses or DOSE_ORDER)]
    v = Vaccine(name=payload.name, code=payload.code, allowed_doses=json.dumps(allowed))
    db.add(v); db.commit(); db.refresh(v)
    return VaccineOut.from_model(v)

@app.get("/vaccines", response_model=List[VaccineOut], dependencies=[Depends(require_api_key)])
def list_vaccines(db: Session = Depends(get_db)):
    return [VaccineOut.from_model(v) for v in db.query(Vaccine).all()]

@app.get("/vaccines/{vid}", response_model=VaccineOut, dependencies=[Depends(require_api_key)])
def get_vaccine(vid: str, db: Session = Depends(get_db)):
    v = db.get(Vaccine, vid)
    if not v:
        raise HTTPException(status_code=404, detail="Vacina não encontrada")
    return VaccineOut.from_model(v)

@app.delete("/vaccines/{vid}", status_code=204, dependencies=[Depends(require_api_key)])
def delete_vaccine(vid: str, db: Session = Depends(get_db)):
    v = db.get(Vaccine, vid)
    if not v:
        raise HTTPException(status_code=404, detail="Vacina não encontrada")
    db.delete(v); db.commit()
    return

# ----------------------- Endpoints: People -----------------------
@app.post("/people", response_model=PersonOut, dependencies=[Depends(require_api_key)], status_code=201)
def create_person(payload: PersonIn, db: Session = Depends(get_db)):
    if db.query(Person).filter_by(document=payload.document).first():
        raise HTTPException(status_code=409, detail="document já existe")
    p = Person(
        name=payload.name,
        document=payload.document,
        sex=payload.sex.value,   # salva como string
        age=payload.age
    )
    db.add(p); db.commit(); db.refresh(p)
    return PersonOut(
        id=p.id, name=p.name, document=p.document,
        sex=GenderEnum(p.sex), age=p.age
    )

@app.get("/people", response_model=List[PersonOut], dependencies=[Depends(require_api_key)])
def list_people(db: Session = Depends(get_db)):
    people = db.query(Person).all()
    return [
        PersonOut(
            id=p.id, name=p.name, document=p.document,
            sex=GenderEnum(p.sex), age=p.age
        ) for p in people
    ]

@app.get("/people/{pid}", response_model=PersonOut, dependencies=[Depends(require_api_key)])
def get_person(pid: str, db: Session = Depends(get_db)):
    p = db.get(Person, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    return PersonOut(
        id=p.id, name=p.name, document=p.document,
        sex=GenderEnum(p.sex), age=p.age
    )

@app.delete("/people/{pid}", status_code=204, dependencies=[Depends(require_api_key)])
def delete_person(pid: str, db: Session = Depends(get_db)):
    p = db.get(Person, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    db.delete(p); db.commit()
    return

# ----------------------- Endpoints: Vaccinations -----------------------
@app.post("/vaccinations", response_model=VaccinationOut, dependencies=[Depends(require_api_key)], status_code=201)
def create_vaccination(
    payload: VaccinationIn,
    db: Session = Depends(get_db),
    enforce_sequence: bool = Query(True)
):
    p = db.get(Person, payload.person_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    v = db.get(Vaccine, payload.vaccine_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vacina não encontrada")

    ensure_dose_allowed(v, payload.dose)
    if enforce_sequence:
        ensure_dose_order(db, payload.person_id, payload.vaccine_id, payload.dose)

    # Proíbe duplicata da mesma dose para a mesma pessoa/vacina
    dup = db.query(Vaccination).filter_by(
        person_id=payload.person_id, vaccine_id=payload.vaccine_id, dose=payload.dose.value
    ).first()
    if dup:
        raise HTTPException(status_code=409, detail="Dose já registrada para esta pessoa e vacina")

    rec = Vaccination(
        person_id=payload.person_id,
        vaccine_id=payload.vaccine_id,
        dose=payload.dose.value,
        applied_at=payload.applied_at,
        lot=payload.lot,
        location=payload.location,
    )
    db.add(rec); db.commit(); db.refresh(rec)
    return VaccinationOut(
        id=rec.id, person_id=rec.person_id, vaccine_id=rec.vaccine_id,
        dose=DoseEnum(rec.dose), applied_at=rec.applied_at,
        lot=rec.lot, location=rec.location, created_at=rec.created_at
    )

@app.get("/vaccinations/{rid}", response_model=VaccinationOut, dependencies=[Depends(require_api_key)])
def get_vaccination(rid: str, db: Session = Depends(get_db)):
    rec = db.get(Vaccination, rid)
    if not rec:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return VaccinationOut(
        id=rec.id, person_id=rec.person_id, vaccine_id=rec.vaccine_id,
        dose=DoseEnum(rec.dose), applied_at=rec.applied_at,
        lot=rec.lot, location=rec.location, created_at=rec.created_at
    )

@app.delete("/vaccinations/{rid}", status_code=204, dependencies=[Depends(require_api_key)])
def delete_vaccination(rid: str, db: Session = Depends(get_db)):
    rec = db.get(Vaccination, rid)
    if not rec:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    db.delete(rec); db.commit()
    return

# ----------------------- Endpoints: Card views -----------------------
@app.get("/people/{pid}/card", dependencies=[Depends(require_api_key)])
def get_card(
    pid: str,
    format: str = Query("list", pattern="^(list|matrix)$"),
    db: Session = Depends(get_db)
):
    p = db.get(Person, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")

    if format == "list":
        blocks: List[CardVaccineBlock] = []
        vaccines = {v.id: v for v in db.query(Vaccine).all()}
        # Agrupa por vacina
        bucket = {}
        for rec in db.query(Vaccination).filter_by(person_id=pid).order_by(Vaccination.applied_at).all():
            bucket.setdefault(rec.vaccine_id, []).append(rec)
        for vid, recs in bucket.items():
            v = vaccines.get(vid)
            entries = [
                CardEntry(
                    record_id=r.id,
                    dose=DoseEnum(r.dose),
                    applied_at=r.applied_at,
                    lot=r.lot,
                    location=r.location
                ) for r in recs
            ]
            blocks.append(CardVaccineBlock(vaccine_id=vid, vaccine_name=v.name if v else vid, entries=entries))
        return CardListOut(
            person=PersonOut(
                id=p.id, name=p.name, document=p.document,
                sex=GenderEnum(p.sex), age=p.age
            ),
            vaccines=blocks
        )

    # matrix
    cols = [MatrixCol(vaccine_id=v.id, vaccine_name=v.name) for v in db.query(Vaccine).order_by(Vaccine.name).all()]
    rows = DOSE_ORDER

    # mapa: (dose, vaccine_id) -> record
    by_key = {}
    for rec in db.query(Vaccination).filter_by(person_id=pid).all():
        by_key[(rec.dose, rec.vaccine_id)] = rec

    grid: List[List[Optional[MatrixCell]]] = []
    for d in rows:
        row_cells: List[Optional[MatrixCell]] = []
        for c in cols:
            r = by_key.get((d.value, c.vaccine_id))
            if r:
                row_cells.append(MatrixCell(record_id=r.id, applied_at=r.applied_at, dose=DoseEnum(r.dose)))
            else:
                row_cells.append(None)
        grid.append(row_cells)

    return CardMatrixOut(
        rows=rows, cols=cols, grid=grid
    )

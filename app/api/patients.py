from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.patient import Envelope, PatientCreate, PatientRead, PatientUpdate
from app.services import patients as service

router = APIRouter(prefix="/patients", tags=["patients"])


def ok(data: object) -> dict:
    return {"data": data, "error": None}


@router.get("", response_model=Envelope)
def list_records(
    last_name: str | None = None,
    date_of_birth: date | None = None,
    phone_number: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    patients = service.list_patients(db, last_name, date_of_birth, phone_number)
    return ok([PatientRead.model_validate(patient) for patient in patients])


@router.get("/{patient_id}", response_model=Envelope)
def get_record(patient_id: UUID, db: Session = Depends(get_db)):
    return ok(PatientRead.model_validate(service.get_patient(db, patient_id)))


@router.post("", response_model=Envelope, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: PatientCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    return ok(PatientRead.model_validate(service.create_patient(db, payload, idempotency_key)))


@router.put("/{patient_id}", response_model=Envelope)
def update_record(patient_id: UUID, payload: PatientUpdate, db: Session = Depends(get_db)):
    return ok(PatientRead.model_validate(service.update_patient(db, patient_id, payload)))


@router.delete("/{patient_id}", response_model=Envelope)
def delete_record(patient_id: UUID, db: Session = Depends(get_db)):
    return ok(PatientRead.model_validate(service.soft_delete_patient(db, patient_id)))


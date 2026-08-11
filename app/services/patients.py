from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate
from app.validation.demographics import normalize_phone


class PatientNotFoundError(Exception):
    pass


class EmptyUpdateError(Exception):
    pass


def list_patients(
    db: Session,
    last_name: str | None = None,
    date_of_birth: date | None = None,
    phone_number: str | None = None,
) -> list[Patient]:
    query = select(Patient).where(Patient.deleted_at.is_(None)).order_by(Patient.created_at.desc())
    if last_name:
        query = query.where(Patient.last_name.ilike(last_name.strip()))
    if date_of_birth:
        query = query.where(Patient.date_of_birth == date_of_birth)
    if phone_number:
        query = query.where(Patient.phone_number == normalize_phone(phone_number))
    return list(db.scalars(query))


def get_patient(db: Session, patient_id: UUID) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.patient_id == patient_id, Patient.deleted_at.is_(None)))
    if not patient:
        raise PatientNotFoundError
    return patient


def create_patient(db: Session, payload: PatientCreate, idempotency_key: str | None = None) -> Patient:
    if idempotency_key:
        existing = db.scalar(select(Patient).where(Patient.idempotency_key == idempotency_key))
        if existing:
            return existing
    patient = Patient(**payload.model_dump(), idempotency_key=idempotency_key)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def update_patient(db: Session, patient_id: UUID, payload: PatientUpdate) -> Patient:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise EmptyUpdateError
    patient = get_patient(db, patient_id)
    merged = {field: getattr(patient, field) for field in PatientCreate.model_fields}
    merged.update(changes)
    validated = PatientCreate.model_validate(merged)
    for field, value in validated.model_dump().items():
        setattr(patient, field, value)
    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)
    return patient


def soft_delete_patient(db: Session, patient_id: UUID) -> Patient:
    patient = get_patient(db, patient_id)
    now = datetime.now(timezone.utc)
    patient.deleted_at = now
    patient.updated_at = now
    db.commit()
    db.refresh(patient)
    return patient


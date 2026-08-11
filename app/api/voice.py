import secrets
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.services import patients as service
from app.validation.demographics import normalize_phone

router = APIRouter(prefix="/voice", tags=["voice-tools"])


def authorize(x_vapi_secret: str | None = Header(default=None)) -> None:
    expected = get_settings().vapi_webhook_secret
    if expected and (not x_vapi_secret or not secrets.compare_digest(x_vapi_secret, expected)):
        raise HTTPException(status_code=401, detail="Invalid voice webhook credentials")


class PhoneLookup(BaseModel):
    phone_number: str


class VoiceCreate(BaseModel):
    call_id: str
    patient: PatientCreate


class VoiceUpdate(BaseModel):
    call_id: str
    patient_id: UUID
    changes: PatientUpdate


@router.post("/tools/find-patient", dependencies=[Depends(authorize)])
def find_patient(payload: PhoneLookup, db: Session = Depends(get_db)) -> dict[str, Any]:
    matches = service.list_patients(db, phone_number=normalize_phone(payload.phone_number))
    return {
        "found": bool(matches),
        "matches": [
            {"patient_id": str(p.patient_id), "first_name": p.first_name, "last_name": p.last_name}
            for p in matches
        ],
    }


@router.post("/tools/create-patient", dependencies=[Depends(authorize)])
def voice_create(payload: VoiceCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    patient = service.create_patient(db, payload.patient, idempotency_key=f"vapi:{payload.call_id}:create")
    return {
        "success": True,
        "message": f"Patient registration saved for {patient.first_name} {patient.last_name}.",
        "patient": PatientRead.model_validate(patient),
    }


@router.post("/tools/update-patient", dependencies=[Depends(authorize)])
def voice_update(payload: VoiceUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    patient = service.update_patient(db, payload.patient_id, payload.changes)
    return {
        "success": True,
        "message": f"Patient information updated for {patient.first_name} {patient.last_name}.",
        "patient": PatientRead.model_validate(patient),
    }


import secrets
import json
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


def authorize(
    x_vapi_secret: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    expected = get_settings().vapi_webhook_secret
    bearer_secret = authorization.removeprefix("Bearer ").strip() if authorization and authorization.startswith("Bearer ") else None
    supplied = x_vapi_secret or bearer_secret
    if expected and (not supplied or not secrets.compare_digest(supplied, expected)):
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


def _tool_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    function = tool_call.get("function") or {}
    arguments = tool_call.get("arguments")
    if arguments is None:
        arguments = tool_call.get("parameters")
    if arguments is None:
        arguments = function.get("arguments")
    if arguments is None:
        arguments = function.get("parameters", {})
    if isinstance(arguments, str):
        return json.loads(arguments)
    return arguments or {}


@router.post("/tools/vapi", dependencies=[Depends(authorize)])
def vapi_tool_dispatch(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    """Handle Vapi's tool-calls envelope and return its required results envelope."""
    # Vapi's dashboard tester posts raw schema parameters, while live calls use
    # the tool-calls envelope. Supporting both makes pre-call verification safe.
    if "message" not in payload:
        if set(payload) == {"phone_number"}:
            phone = normalize_phone(str(payload["phone_number"]))
            matches = service.list_patients(db, phone_number=phone)
            return {
                "found": bool(matches),
                "matches": [
                    {"patient_id": str(p.patient_id), "first_name": p.first_name, "last_name": p.last_name}
                    for p in matches
                ],
            }
        if "patient_id" in payload and "changes" in payload:
            patient = service.update_patient(
                db,
                UUID(str(payload["patient_id"])),
                PatientUpdate.model_validate(payload["changes"]),
            )
            return {"success": True, "patient_id": str(patient.patient_id)}
        patient = service.create_patient(
            db,
            PatientCreate.model_validate(payload.get("patient", payload)),
            idempotency_key=payload.get("idempotency_key"),
        )
        return {"success": True, "patient_id": str(patient.patient_id)}

    message = payload.get("message", {})
    tool_calls = message.get("toolCallList", [])
    call_id = str(message.get("call", {}).get("id", "unknown-call"))
    results: list[dict[str, str]] = []

    for tool_call in tool_calls:
        tool_call_id = str(tool_call.get("id", "unknown-tool-call"))
        name = tool_call.get("name") or tool_call.get("function", {}).get("name")
        try:
            arguments = _tool_arguments(tool_call)
            if name == "find_patient_by_phone":
                phone = normalize_phone(arguments["phone_number"])
                matches = service.list_patients(db, phone_number=phone)
                output = {
                    "found": bool(matches),
                    "matches": [
                        {"patient_id": str(p.patient_id), "first_name": p.first_name, "last_name": p.last_name}
                        for p in matches
                    ],
                }
            elif name == "create_patient":
                patient_payload = arguments.get("patient", arguments)
                patient = service.create_patient(
                    db,
                    PatientCreate.model_validate(patient_payload),
                    idempotency_key=f"vapi:{call_id}:create",
                )
                output = {
                    "success": True,
                    "message": f"Patient registration saved for {patient.first_name} {patient.last_name}.",
                    "patient_id": str(patient.patient_id),
                }
            elif name == "update_patient":
                patient = service.update_patient(
                    db,
                    UUID(str(arguments["patient_id"])),
                    PatientUpdate.model_validate(arguments.get("changes", {})),
                )
                output = {
                    "success": True,
                    "message": f"Patient information updated for {patient.first_name} {patient.last_name}.",
                    "patient_id": str(patient.patient_id),
                }
            else:
                raise ValueError(f"Unknown tool: {name}")
            results.append({"toolCallId": tool_call_id, "result": json.dumps(output, separators=(",", ":"))})
        except Exception as exc:
            db.rollback()
            results.append({"toolCallId": tool_call_id, "error": f"Tool failed: {str(exc)}"})

    return {"results": results}


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

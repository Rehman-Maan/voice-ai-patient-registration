from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.patient import Sex
from app.validation.demographics import (
    normalize_phone,
    normalize_spaces,
    normalize_state,
    validate_dob,
    validate_member_id,
    validate_name,
    validate_zip,
)


class PatientFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    phone_number: str
    email: EmailStr | None = None
    address_line_1: Annotated[str, Field(min_length=1, max_length=200)]
    address_line_2: Annotated[str | None, Field(max_length=100)] = None
    city: Annotated[str, Field(min_length=1, max_length=100)]
    state: str
    zip_code: str
    insurance_provider: Annotated[str | None, Field(max_length=150)] = None
    insurance_member_id: Annotated[str | None, Field(max_length=100)] = None
    preferred_language: Annotated[str, Field(min_length=1, max_length=50)] = "English"
    emergency_contact_name: Annotated[str | None, Field(max_length=100)] = None
    emergency_contact_phone: str | None = None

    _first_name = field_validator("first_name")(validate_name)
    _last_name = field_validator("last_name")(validate_name)
    _dob = field_validator("date_of_birth")(validate_dob)
    _phone = field_validator("phone_number")(normalize_phone)
    _state = field_validator("state")(normalize_state)
    _zip = field_validator("zip_code")(validate_zip)

    @field_validator("address_line_1", "address_line_2", "city", "insurance_provider", "preferred_language", "emergency_contact_name")
    @classmethod
    def clean_spaces(cls, value: str | None) -> str | None:
        return normalize_spaces(value) if value is not None else None

    @field_validator("insurance_member_id")
    @classmethod
    def member_id(cls, value: str | None) -> str | None:
        return validate_member_id(value) if value else value

    @field_validator("emergency_contact_phone")
    @classmethod
    def emergency_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else value

    @model_validator(mode="after")
    def emergency_contact_pair(self):
        if bool(self.emergency_contact_name) != bool(self.emergency_contact_phone):
            raise ValueError("emergency contact name and phone must be supplied together")
        return self


class PatientCreate(PatientFields):
    pass


class PatientUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    sex: Sex | None = None
    phone_number: str | None = None
    email: EmailStr | None = None
    address_line_1: Annotated[str | None, Field(min_length=1, max_length=200)] = None
    address_line_2: Annotated[str | None, Field(max_length=100)] = None
    city: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    state: str | None = None
    zip_code: str | None = None
    insurance_provider: Annotated[str | None, Field(max_length=150)] = None
    insurance_member_id: Annotated[str | None, Field(max_length=100)] = None
    preferred_language: Annotated[str | None, Field(min_length=1, max_length=50)] = None
    emergency_contact_name: Annotated[str | None, Field(max_length=100)] = None
    emergency_contact_phone: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def names(cls, value: str | None) -> str | None:
        return validate_name(value) if value is not None else None

    @field_validator("date_of_birth")
    @classmethod
    def dob(cls, value: date | None) -> date | None:
        return validate_dob(value) if value is not None else None

    @field_validator("phone_number", "emergency_contact_phone")
    @classmethod
    def phones(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else value

    @field_validator("state")
    @classmethod
    def state_code(cls, value: str | None) -> str | None:
        return normalize_state(value) if value else value

    @field_validator("zip_code")
    @classmethod
    def postal_code(cls, value: str | None) -> str | None:
        return validate_zip(value) if value else value

    @field_validator("insurance_member_id")
    @classmethod
    def member_id(cls, value: str | None) -> str | None:
        return validate_member_id(value) if value else value


class PatientRead(PatientFields):
    model_config = ConfigDict(from_attributes=True)

    patient_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict] | None = None
    request_id: str | None = None


class Envelope(BaseModel):
    data: object | None = None
    error: ErrorDetail | None = None


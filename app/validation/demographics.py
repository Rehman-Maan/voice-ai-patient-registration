import re
from datetime import date

import phonenumbers


US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}
NAME_PATTERN = re.compile(r"^[A-Za-z]+(?:[ '\-][A-Za-z]+)*$")
ZIP_PATTERN = re.compile(r"^\d{5}(?:-\d{4})?$")
MEMBER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ./\-]*$")


def normalize_spaces(value: str) -> str:
    return " ".join(value.strip().split())


def validate_name(value: str) -> str:
    value = normalize_spaces(value)
    if not 1 <= len(value) <= 50 or not NAME_PATTERN.fullmatch(value):
        raise ValueError("must be 1-50 letters and may include spaces, hyphens, or apostrophes")
    return value


def validate_dob(value: date) -> date:
    if value > date.today():
        raise ValueError("date of birth cannot be in the future")
    return value


def normalize_phone(value: str) -> str:
    try:
        parsed = phonenumbers.parse(value, "US")
    except phonenumbers.NumberParseException as exc:
        raise ValueError("must be a valid 10-digit U.S. phone number") from exc
    if parsed.country_code != 1 or not phonenumbers.is_valid_number(parsed):
        raise ValueError("must be a valid 10-digit U.S. phone number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def normalize_state(value: str) -> str:
    value = value.strip().upper()
    if value not in US_STATES:
        raise ValueError("must be a valid two-letter U.S. state abbreviation")
    return value


def validate_zip(value: str) -> str:
    value = value.strip()
    if not ZIP_PATTERN.fullmatch(value):
        raise ValueError("must be a 5-digit ZIP code or ZIP+4")
    return value


def validate_member_id(value: str) -> str:
    value = normalize_spaces(value)
    if not MEMBER_ID_PATTERN.fullmatch(value):
        raise ValueError("must be an alphanumeric member ID")
    return value


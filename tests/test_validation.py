from datetime import date, timedelta

import pytest

from app.validation.demographics import normalize_phone, normalize_state, validate_dob, validate_name, validate_zip
from app.config import Settings


def test_normalizers():
    assert validate_name("  Mary   O'Neil-Smith ") == "Mary O'Neil-Smith"
    assert normalize_phone("(732) 555-0147") == "+17325550147"
    assert normalize_state("nj") == "NJ"
    assert validate_zip("08873-1234") == "08873-1234"


@pytest.mark.parametrize("value", ["", "123", "Jane@Doe", "A" * 51])
def test_invalid_names(value):
    with pytest.raises(ValueError):
        validate_name(value)


def test_future_dob():
    with pytest.raises(ValueError):
        validate_dob(date.today() + timedelta(days=1))


def test_platform_postgres_url_uses_psycopg3():
    settings = Settings(database_url="postgresql://user:pass@db:5432/app")
    assert settings.sqlalchemy_database_url == "postgresql+psycopg://user:pass@db:5432/app"

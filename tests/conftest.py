import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["VAPI_WEBHOOK_SECRET"] = "test-secret"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def patient_payload():
    return {
        "first_name": "Jane",
        "last_name": "O'Neil-Smith",
        "date_of_birth": "1990-05-20",
        "sex": "Female",
        "phone_number": "732-555-0147",
        "email": "jane@example.com",
        "address_line_1": "7 Clyde Road",
        "address_line_2": None,
        "city": "Somerset",
        "state": "NJ",
        "zip_code": "08873",
        "preferred_language": "English",
    }


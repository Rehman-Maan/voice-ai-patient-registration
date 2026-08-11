import os

import httpx


base_url = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")
payload = {
    "first_name": "Demo",
    "last_name": "Patient",
    "date_of_birth": "1992-04-15",
    "sex": "Decline to Answer",
    "phone_number": "202-555-0147",
    "address_line_1": "100 Demo Avenue",
    "city": "Washington",
    "state": "DC",
    "zip_code": "20001",
}

with httpx.Client(base_url=base_url, timeout=15) as client:
    health = client.get("/health")
    health.raise_for_status()
    created = client.post("/patients", json=payload, headers={"Idempotency-Key": "deployment-smoke-v1"})
    created.raise_for_status()
    patient = created.json()["data"]
    fetched = client.get(f"/patients/{patient['patient_id']}")
    fetched.raise_for_status()
    assert fetched.json()["data"]["phone_number"] == "+12025550147"
    print({"health": health.json(), "patient_id": patient["patient_id"], "status": "passed"})


def test_crud_filters_and_soft_delete(client, patient_payload):
    created = client.post("/patients", json=patient_payload)
    assert created.status_code == 201
    body = created.json()
    assert body["error"] is None
    patient_id = body["data"]["patient_id"]
    assert body["data"]["phone_number"] == "+17325550147"

    assert len(client.get("/patients?last_name=O'Neil-Smith").json()["data"]) == 1
    assert len(client.get("/patients?date_of_birth=1990-05-20").json()["data"]) == 1
    assert len(client.get("/patients?phone_number=7325550147").json()["data"]) == 1

    updated = client.put(f"/patients/{patient_id}", json={"city": "New Brunswick"})
    assert updated.status_code == 200
    assert updated.json()["data"]["city"] == "New Brunswick"

    deleted = client.delete(f"/patients/{patient_id}")
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted_at"] is not None
    assert client.get(f"/patients/{patient_id}").status_code == 404
    assert client.get("/patients").json()["data"] == []


def test_validation_envelope(client, patient_payload):
    patient_payload["date_of_birth"] = "2999-01-01"
    response = client.post("/patients", json=patient_payload)
    assert response.status_code == 422
    assert response.json()["data"] is None
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_empty_update_returns_400(client, patient_payload):
    patient_id = client.post("/patients", json=patient_payload).json()["data"]["patient_id"]
    response = client.put(f"/patients/{patient_id}", json={})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_UPDATE"


def test_idempotent_create(client, patient_payload):
    headers = {"Idempotency-Key": "call-123"}
    first = client.post("/patients", json=patient_payload, headers=headers)
    second = client.post("/patients", json=patient_payload, headers=headers)
    assert first.json()["data"]["patient_id"] == second.json()["data"]["patient_id"]
    assert len(client.get("/patients").json()["data"]) == 1


def test_root_guides_reviewers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "online"
    assert response.json()["data"]["documentation"] == "/docs"

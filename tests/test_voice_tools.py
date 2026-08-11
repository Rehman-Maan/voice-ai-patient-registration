def test_voice_auth_lookup_and_idempotent_create(client, patient_payload):
    unauthorized = client.post("/voice/tools/find-patient", json={"phone_number": "7325550147"})
    assert unauthorized.status_code == 401

    headers = {"X-Vapi-Secret": "test-secret"}
    payload = {"call_id": "call-abc", "patient": patient_payload}
    first = client.post("/voice/tools/create-patient", json=payload, headers=headers)
    second = client.post("/voice/tools/create-patient", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["patient"]["patient_id"] == second.json()["patient"]["patient_id"]

    lookup = client.post("/voice/tools/find-patient", json={"phone_number": "7325550147"}, headers=headers)
    assert lookup.json()["found"] is True
    assert lookup.json()["matches"][0]["first_name"] == "Jane"


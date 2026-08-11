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


def test_vapi_envelope_dispatches_and_returns_matching_tool_call_id(client, patient_payload):
    headers = {"X-Vapi-Secret": "test-secret"}
    envelope = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "vapi-call-123"},
            "toolCallList": [
                {"id": "tool-call-456", "name": "create_patient", "arguments": {"patient": patient_payload}}
            ],
        }
    }
    response = client.post("/voice/tools/vapi", json=envelope, headers=headers)
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["toolCallId"] == "tool-call-456"
    assert '"success":true' in result["result"]


def test_vapi_errors_still_return_200_with_tool_error(client):
    headers = {"X-Vapi-Secret": "test-secret"}
    envelope = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "vapi-call-error"},
            "toolCallList": [{"id": "tool-error", "name": "unknown_tool", "arguments": {}}],
        }
    }
    response = client.post("/voice/tools/vapi", json=envelope, headers=headers)
    assert response.status_code == 200
    assert response.json()["results"][0]["toolCallId"] == "tool-error"
    assert "error" in response.json()["results"][0]

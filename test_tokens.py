from app.services.tokens import create_access_token, verify_access_token


def test_access_token_round_trip():
    token = create_access_token(
        patient_id="patient-123",
        email="patient@example.com",
    )

    payload = verify_access_token(token)

    assert payload["sub"] == "patient-123"
    assert payload["email"] == "patient@example.com"


def test_access_token_rejects_tampering():
    token = create_access_token(
        patient_id="patient-123",
        email="patient@example.com",
    )
    header, payload, signature = token.split(".")
    tampered_payload = f"{payload[:-1]}x"
    tampered = ".".join([header, tampered_payload, signature])

    assert verify_access_token(tampered) is None
